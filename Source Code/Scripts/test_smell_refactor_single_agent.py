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

def build_prompts(test_smell_name: str, test_smell_definition_and_refactoring: str) -> PromptTemplate:
    return PromptTemplate(
        input_variables=["code"],
        template=f"""
You are a coding assistant specializing in test code analysis and refactoring, with many years of experience.
{test_smell_definition_and_refactoring}

Your task:
Analyze the provided test code to identify and resolve occurrences of "{test_smell_name}".
If no such smell is present, return the original code unchanged. Ensure that the refactored test maintains the same behavior while eliminating the {test_smell_name}.
Finally, output only the final refactored code, ensuring it is valid under JUnit 5 and free of compilation errors, without providing any additional explanations or text.

Code to analyze:
{code}
"""
    )


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

    prompt = build_prompts(smell_name, smell_def)
    llm = OllamaLLM(model=args.model, base_url=args.base_url,
                    temperature=args.temperature)
    single = LLMChain(llm=llm, prompt=prompt)

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
                ref = single.run(code=code, explanation=explanation)
                df.at[idx, f"Refactored code"] = ref

                print(f"\n===== Test {idx+1} =====\n")
                print(f"Test Code: \n {code}")
                print(f"{idx + 1}. Result: {ref}\n===========\n")
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
