# Test Smell Detection and Refactoring with Agentic Workflows

This folder contains the code used to detect and refactor test smells with single-agent and four-agent pipelines, using an open model served by [Ollama](https://ollama.com/) and orchestrated with LangChain.

Two equivalent implementations are provided, so you can pick whichever fits your setup:

* **Notebooks** (`test_smell_refactor_single_agent.ipynb`, `test_smell_refactor_multi_agent.ipynb`): the versions used to produce the results reported in the paper. Best for Google Colab (free GPU) or a local Jupyter environment.
* **Scripts** (`Scripts/test_smell_refactor_single_agent.py`, `Scripts/test_smell_refactor_multi_agent.py`): a command-line version with the same logic and the same prompts, convenient for running locally without a notebook.

Both read the same dataset and the same smell definitions, and produce the same output columns.

---

## Folder structure

```
Source Code/
|-- test_smell_refactor_single_agent.ipynb    # single-agent notebook (Colab/Jupyter)
|-- test_smell_refactor_multi_agent.ipynb     # four-agent notebook (Colab/Jupyter)
|-- test_smell_definitions_and_refactorings.txt
`-- Scripts/
    |-- test_smell_refactor_single_agent.py   # single-agent script (CLI)
    |-- test_smell_refactor_multi_agent.py    # four-agent script (CLI)
    |-- test_smell_definitions_and_refactorings.txt
    `-- requirements.txt
```

The dataset is provided at the repository root, in the `Dataset/` folder, as one CSV per smell.

---

## Requirements

* **Python 3.10+**
* **Ollama runtime** ([install instructions](https://ollama.com/))
  * Linux/macOS: `curl -fsSL https://ollama.com/install.sh | sh`
  * Windows: download the installer from the Ollama website.
* A machine able to serve the chosen model. The results in the paper use `gemma4:31b`, which needs roughly 20-24 GB of memory under the default 4-bit quantization. For a quick functional test, a small model such as `llama3.2:3b` (~2 GB) runs on a modest machine.

---

## Dataset

The `Dataset/` folder already contains one ready-to-use CSV per smell:

* `Dataset - Assertion Roulette.csv`
* `Dataset - Conditional Test.csv`
* `Dataset - Duplicate Assert.csv`
* `Dataset - Exception Handling.csv`
* `Dataset - Magic Number.csv`

Each CSV has the columns `Id`, `LLM`, `Date`, `Test Smell`, `Language`, `Project`, `URL`, `Method`, `Test Code`, and `Line Count`. The pipelines read the test code from the `Test Code` column, so any custom CSV must include that column. No conversion or export step is needed: point the run command directly at the CSV of the smell you want to process.

---

## Option A: Run the notebooks (Colab or Jupyter)

1. Open the desired notebook (`..._single_agent.ipynb` or `..._multi_agent.ipynb`) in Google Colab or in a local Jupyter environment.
2. Upload (or place next to the notebook) the CSV of the smell you want to run and the `test_smell_definitions_and_refactorings.txt` file.
3. Set the parameters in the widgets (smell name, model tag, temperature, and, for the multi-agent notebook, the number of iterations).
4. Run all cells. The notebook installs the dependencies, starts Ollama, pulls the model, processes each instance, and writes the output CSV.

The notebooks were the ones used to generate the results reported in the paper, running the model `gemma4:31b` on a Google Colab instance with an NVIDIA A100 GPU.

---

## Option B: Run the scripts (command line)

### 1. Install the dependencies

From the `Scripts/` folder:

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks the activation script, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, then activate again.

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> The `requirements.txt` pins the library versions that are known to work. Please keep the pinned versions: newer LangChain releases move some imports and would break the scripts.

Make sure the Ollama runtime is installed and available. The scripts automatically start the Ollama server and pull the model tag passed with `--model`.

### 2. Run

Point `--csv` at the CSV of the smell you want to process (from the `Dataset/` folder) and `--smell` at the matching smell name. The examples below assume the CSV is in the current folder; adjust the path if you run from `Scripts/`.

**Single-agent**

```bash
python test_smell_refactor_single_agent.py --csv "Dataset - Duplicate Assert.csv" --definitions test_smell_definitions_and_refactorings.txt --smell "Duplicate Assert" --model gemma4:31b --temperature 0.6 --out out_single.csv
```

**Four-agent**

```bash
python test_smell_refactor_multi_agent.py --csv "Dataset - Duplicate Assert.csv" --definitions test_smell_definitions_and_refactorings.txt --smell "Duplicate Assert" --model gemma4:31b --temperature 0.6 --max_iters 3 --out out_multi.csv
```

Notes:

* On Windows, use `python` (not `python3`).
* Wrap any file name or smell name that contains spaces in quotes, e.g. `"Dataset - Duplicate Assert.csv"` and `"Magic Number Test"`.
* To only check that everything runs, replace `--model gemma4:31b` with a small model such as `--model llama3.2:3b`. This is a functional test only; reproducing the paper's results requires `gemma4:31b`.
* The four-agent pipeline makes several model calls per instance, so it takes noticeably longer than the single-agent one.
* If you omit `--out`, results are saved automatically to `data/output/<csv-file>-<smell>.csv`.

---

## Definition file format

`test_smell_definitions_and_refactorings.txt` contains the definition and refactoring instructions for each smell. At runtime, only the block matching the `--smell` argument (or the notebook widget) is loaded. Each block follows this format:

```
test_smell_name = "Smell Name"
test_smell_definition = """
...definition and refactoring instructions...
"""
```

New smells can be added by copying a block and editing `test_smell_name` and `test_smell_definition`. No code changes are required.

---

## Command-line flags (scripts)

| Flag | Default | Description |
|------|---------|-------------|
| `--csv` | *required* | Input CSV; **must contain a column named `Test Code`** |
| `--definitions` | `test_smell_definitions_and_refactorings.txt` | File with the smell definitions |
| `--smell` | *required* | Exact smell name to run |
| `--model` | `phi4` | Ollama model tag (use `gemma4:31b` to reproduce the paper) |
| `--temperature` | `0.6` | Sampling temperature |
| `--base_url` | `http://localhost:11434` | Ollama server URL |
| `--max_iters` | `3` | Evaluator-Optimizer loop limit (four-agent only) |
| `--out` | auto-named file in `data/output/` | Output CSV path |

---

## Output

* **Single-agent:** the output CSV extends the input with the columns `LLM`, `Test Smell`, `Date`, and `Refactored code`.
* **Four-agent:** the output CSV records the decisions of each iteration (detection, agreement, refactored code, and verification) for up to `--max_iters` rounds.
* Every run also writes a log of the full agent dialogue to `agents.txt`.

The raw outputs produced for the paper are available in the `Outputs Gemma4-31B/` folder (per smell, for both configurations), and the consolidated evaluation and execution times are in the `Results/` folder.

---

## Note on warnings

When running with the pinned library versions, you may see `LangChainDeprecationWarning` (for `LLMChain` and `.run`) and a pandas `FutureWarning` about dtype. These are harmless with the pinned versions and do not affect the output.