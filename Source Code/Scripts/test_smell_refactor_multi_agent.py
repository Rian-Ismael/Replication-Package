#!/usr/bin/env python3
# coding: utf-8

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from datetime import date
from pathlib import Path

import pandas as pd
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain


def ensure_ollama(cmd: str = "ollama") -> None:
    """Abort if the Ollama CLI is not on PATH."""
    if shutil.which(cmd):
        return
    sys.exit(
        "Ollama CLI not found.\n"
        "Install it with: curl -fsSL https://ollama.com/install.sh | sh"
    )


def start_ollama() -> None:
    """Run `ollama serve` in background if it is not already running."""
    def _run() -> None:
        os.environ["OLLAMA_HOST"] = "0.0.0.0:11434"
        os.environ["OLLAMA_ORIGINS"] = "*"
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    threading.Thread(target=_run, daemon=True).start()
    time.sleep(1)


code = "{code}"
agent_feedback = "{agent_feedback}"
agent_answer = "{agent_answer}"
refactored_code = "{refactored_code}"
reviewer_feedback = "{reviewer_feedback}"


def build_prompts(test_smell_name: str, test_smell_definition_and_refactoring: str) -> dict[str, PromptTemplate]:
    detect = PromptTemplate(
        input_variables=["code", "agent_feedback"],
        template=f"""
You are a coding assistant with many years of experience that detects test smells.
{test_smell_definition_and_refactoring}

Your goal is to determine if the provided test code exhibits the test smell "{test_smell_name}".
{code}
Next I may give you further details.
{agent_feedback}
If the test code contains {test_smell_name}, respond with EXACTLY "YES" on the first line and explain why. Ignore code comments. If it does not contain, say EXACTLY "NO" on the first line and explain why not.
"""
    )
    eval_detect = PromptTemplate(
        input_variables=["code", "agent_answer"],
        template=f"""
You are a coding expert reviewing the detection of a test smell. Consider the following test smell.
{test_smell_definition_and_refactoring}

A previous agent analyzed the following test code.
{code}
It gave the following answer.
{agent_answer}
Your goal is to evaluate if the previous detection by another agent is correct and justified. Ignore code comments.
If you do not agree, answer NO and explain what's wrong with it and what to correct.
If yes, just say YES.
"""
    )
    refactor = PromptTemplate(
        input_variables=["code", "reviewer_feedback"],
        template=f"""
You are a coding assistant specializing in test code analysis and refactoring, with many years of experience.

{test_smell_definition_and_refactoring}

Your task is as follows.
First analyze the provided test code to resolve test smell occurrences "{test_smell_name}". If there is no smell, output the original code unchanged.
Second ensure the test preserves the same behavior, but is free of {test_smell_name}.
Third output only the final refactored code, valid under JUnit 5.
Finally check the refactored version does not introduce compilation errors.

Provide only the final refactored code, with no additional explanation or text.
Code to analyze:
{code}

Next I may provide you further details.
{reviewer_feedback}
"""
    )
    eval_refactor = PromptTemplate(
        input_variables=["refactored_code"],
        template=f"""
You are a code reviewer specializing in JUnit 5 test smells.
{test_smell_definition_and_refactoring}

Analyze the following code.
{refactored_code}

Your task is to check three conditions.
First check the code does not have the test smell {test_smell_name}.
Second verify the code follows JUnit 5 specification.
Finally confirms the code does not have compilation errors.

If the code satisfy all conditons, respond with EXACTLY "YES" on the first line.
If not, respond with EXACTLY "NO" on the first line, then explain in one or two sentences why.

Let's think step by step.
"""
    )
    return {
        "detect": detect,
        "eval_detect": eval_detect,
        "refactor": refactor,
        "eval_refactor": eval_refactor,
    }


def load_smell(def_file: Path, smell_name: str) -> tuple[str, str]:
    """Extract the smell block that matches `smell_name` from the definitions file."""
    txt = def_file.read_text(encoding="utf-8")
    pat = re.compile(
        r'test_smell_name\s*=\s*"([^"]+)"\s*[\r\n]+'
        r'test_smell_definition\s*=\s*"""(.*?)"""',
        re.S,
    )
    for name, definition in pat.findall(txt):
        if name.strip().lower() == smell_name.lower():
            return name.strip(), definition.strip()
    sys.exit(f'Smell "{smell_name}" not found in {def_file}')


def main() -> None:
    ap = argparse.ArgumentParser("Detect / Refactor Test Smells via Ollama")
    ap.add_argument("--csv", required=True, help="CSV containing column 'Test Code'")
    ap.add_argument("--definitions", default="test_smell_definitions_and_refactorings.txt",
                    help="Text file with multiple smells in Python‑like blocks")
    ap.add_argument("--smell", required=True, help="Exact Test Smell name to run")
    ap.add_argument("--model", default="phi4")
    ap.add_argument("--temperature", type=float, default=0.6)
    ap.add_argument("--base_url", default="http://localhost:11434")
    ap.add_argument("--max_iters", type=int, default=3)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    smell_name, smell_def = load_smell(Path(args.definitions), args.smell)

    ensure_ollama()
    start_ollama()
    subprocess.run(["ollama", "pull", args.model], check=True)

    prompts = build_prompts(smell_name, smell_def)
    llm = OllamaLLM(model=args.model, base_url=args.base_url,
                    temperature=args.temperature)
    chain_detect = LLMChain(llm=llm, prompt=prompts["detect"])
    chain_eval_detect = LLMChain(llm=llm, prompt=prompts["eval_detect"])
    chain_refactor = LLMChain(llm=llm, prompt=prompts["refactor"])
    chain_eval_refactor = LLMChain(llm=llm, prompt=prompts["eval_refactor"])

    df = pd.read_csv(args.csv)
   
    today = date.today()
    today_str = today.strftime("%Y-%m-%d")
    for c in ["LLM", "Test Smell", "Date"]:
        if c not in df.columns:
            df[c] = ""

    with open("agents.txt", "w", encoding="utf-8") as log:
        original_stdout = sys.stdout
        sys.stdout = log
        try:
            for idx, row in df.iterrows():
                code = "@Test\n" + str(row.get("Test Code", "")).strip()
                df.loc[idx, ["LLM", "Test Smell", "Date"]] = [str(args.model), str(smell_name), today_str]
                explanation = ""
                confirmed = False
                print(f"\n===== Test {idx+1} =====\n")
                print(f"Test Code: \n {code}")
                for it in range(1, args.max_iters + 1):
                    r1 = chain_detect.run(code=code, agent_feedback=explanation)
                    r2 = chain_eval_detect.run(code=code, agent_answer=r1)
                    df.at[idx, f"{it}° - Detected smell?"] = (
                        "YES" if "yes" in r1.lower() else "NO")
                    df.at[idx, f"{it}° - Do you agree with detection?"] = (
                        "YES" if "yes" in r2.lower() else "NO")
                    print(f"[Detection Iter {it}]")
                    print(f"1.{it}. Agent 1 Result: {r1}\n===========\n")
                    print(f"1.{it}. Agent 2 Result: {r2}\n===========\n")
                    print("------------------------------------------------")
                    if "yes" in r2.lower():
                        confirmed, explanation = True, r1
                        break
                    explanation = r1
                if not confirmed:
                    print("Test smell not confirmed. Skipping refactoring.")
                    continue
                if not "yes" in r1.lower():
                    print("Test smell not detected. Skipping refactoring.")
                    continue

                current, feedback = code, explanation
                for it in range(1, args.max_iters + 1):
                    ref = chain_refactor.run(code=current,
                                             reviewer_feedback=feedback)
                    chk = chain_eval_refactor.run(refactored_code=ref)
                    df.at[idx, f"{it}° - Refactored code"] = ref
                    ok = "yes" in chk.lower()
                    df.at[idx, f"{it}° -  LLM - Is there still a test smell?"] = (
                        "NO" if ok else "YES")
                    print(f"2.{it}. Agent 3 Result: {ref}\n===========\n")
                    print(f"2.{it}. Agent 4 Result: {chk}\n===========\n")
                    print("=================================================")
                    if ok:
                        break
                    feedback = "\n".join(chk.splitlines()[1:]) or "No explanation"
                    current = ref
        finally:
            sys.stdout = original_stdout

    out_csv = Path(args.out) if args.out else \
              Path("data/output") / f"{Path(args.csv).stem}-{smell_name.replace(' ', '_')}.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)
    print(f"Results saved to: {out_csv}")
    print("Agent log written to agents.txt")


if __name__ == "__main__":
    main()