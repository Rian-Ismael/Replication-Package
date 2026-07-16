# Replicating Agentic Workflows for Test Smell Detection and Refactoring with Gemma-4-31B

Replication package for the study on test smell detection and refactoring with agentic pipelines, applied to the open model **Gemma-4-31B** served locally through Ollama. This work reproduces the protocol of Melo et al. (IEEE Software, 2026), replacing the model with a more recent version while keeping the same dataset, the same prompts, and the same correctness criteria, over the same 150 instances, and comparing a single-agent pipeline against a four-agent one.

Author: Rian Melo (UFCG, Campina Grande, PB, Brazil).

## Goal

The study addresses two research questions:

* **RQ1:** Within an agentic pipeline, does Gemma-4-31B refactor test smells at a level comparable to proprietary LLMs (o3, Claude-4-Sonnet, Gemini-2.5-Pro)?
* **RQ2:** For Gemma-4-31B, does a four-agent pipeline outperform a single-agent one in detection and refactoring?

With a single agent and a single attempt, Gemma-4-31B correctly refactored 78.7% of the instances, surpassing the proprietary models reported in the original study. The four-agent pipeline showed no gain, tying on three smell types, performing worse on two, and requiring considerably more execution time.

## Repository structure

```
.
├── Dataset/
│   └── Dataset.xlsx                      # 150 instances (5 sheets, one per smell)
├── Source Code/
│   ├── test_smell_refactor_single_agent.ipynb   # single-agent pipeline
│   ├── test_smell_refactor_multi_agent.ipynb    # four-agent pipeline
│   └── test_smell_definitions_and_refactorings.txt  # smell definitions (notebook input)
├── Outputs Gemma4-31B/
│   ├── Single/                           # single-agent pipeline outputs
│   │   ├── Assertion Roulette/           # output_*.csv + agente_single_*.txt
│   │   ├── Conditional Test Logic/
│   │   ├── Duplicate Assert/
│   │   ├── Exception Handling/
│   │   └── Magic Number/
│   └── Multi/                            # four-agent pipeline outputs
│       ├── Assertion Roulette/           # output_*.csv + agentes_multi_*.txt
│       ├── Conditional Test Logic/
│       ├── Duplicate Assert/
│       ├── Exception Handling/
│       └── Magic Number/
└── Gemma4-31B-Results.xlsx              # consolidated spreadsheet (evaluation and times)
```

## Dataset

The set reuses the 150 instances from the base study, extracted from 11 open-source Java systems that use JUnit 5: janusgraph, quarkus, testcontainers-java, opengrok, jenkins, lettuce, Mindustry, data-transfer-project, Activiti, flowable-engine, and skywalking. There are five smell types, with 30 instances each. Following the original criterion, only test methods with at most 30 lines of code are considered.

Definitions adopted for each smell type, following the original study:

| Smell | Definition and refactoring |
|---|---|
| **Assertion Roulette** | Occurs when a test method contains more than one assertion statement without an explanation or message (parameter in the assertion method). To mitigate this smell, developers should add a message to each assertion. |
| **Conditional Test Logic** | Arises when a test method contains one or more control statements (i.e., conditional expression, and loop statements). This can be addressed by having the developer create a dedicated test method for each condition. |
| **Duplicate Assert** | Appears when a test method contains more than one assertion statement with the same parameters. To address this, developers should split assertions that test different scenarios or states into separate tests for clarity. |
| **Exception Handling** | Occurs when a test method contains either a `throw` statement or at least a `catch` clause. To avoid this smell, use the testing framework's features (e.g., `assertThrows`) instead of manually catching or throwing exceptions. |
| **Magic Number** | Occurs when a test method contains an assertion with a numeric literal as an argument. Refactoring involves extracting and initializing all magic numbers into constants or local variables with descriptive names. |

`Dataset.xlsx` contains one sheet per smell, with the columns `Id`, `LLM`, `Date`, `Test Smell`, `Language`, `Project`, `URL`, `Method`, `Test Code`, and `Line Count`. The notebooks read the dataset in CSV format (`Dataset.csv`, via `pd.read_csv`), corresponding to one smell at a time. To reproduce, export the sheet of the desired smell from `Dataset.xlsx` as CSV and point the `csv_path` parameter to that file (or save it as `Dataset.csv`).

## Pipelines

Both pipelines use LangChain for orchestration and Ollama to serve the model. The prompts employ the Persona and Chain-of-Thought strategies and are reused without modification from the original study.

**Single agent.** A single agent receives the smell definition and the test code and, in a single pass, detects the smell and rewrites the code. When no smell is present, the original code is returned.

**Four agents.** The task is distributed across four agents, with an Evaluator-Optimizer loop that repeats up to three times (`max_iters = 3`):

1. **Agent 1** detects the smell, answering `YES` or `NO` on the first line with a justification.
2. **Agent 2** evaluates Agent 1's detection; on disagreement, it returns `NO` with what to correct, and the detection loop restarts with that feedback.
3. **Agent 3** refactors the code, preserving behavior and keeping it valid under JUnit 5.
4. **Agent 4** checks that the refactored code no longer contains the smell, follows the JUnit 5 specification, and introduces no compilation errors; if not, it returns `NO` with an explanation, and the refactoring loop restarts.

The two-agent variant is omitted for cost reasons, since the original results placed it between the single- and four-agent configurations.

## Execution environment

Model `gemma4:31b` served by Ollama and accessed by the LangChain pipeline, executed in a Google Colab environment with an NVIDIA A100 GPU, using the default configuration of the reference notebook from the original study (sampling temperature `0.6`). The exact model identifier is recorded in the package.

## Reproduction

Requirements in the environment before execution: the smell CSV (exported from `Dataset.xlsx`), the definitions file `test_smell_definitions_and_refactorings.txt` (in `Source Code/`), and a reachable Ollama server. The definitions file follows the format read by the `load_smell` function:

```
test_smell_name = "Smell Name"
test_smell_definition = """
...definition and refactoring instructions...
"""
```

Each notebook exposes the following parameters:

| Parameter | Default | Description |
|---|---|---|
| `csv_path` | `Dataset.csv` | CSV with the test cases. |
| `definitions_path` | `test_smell_definitions_and_refactorings.txt` | Smell definitions file. |
| `smell` | one of the five smells | Smell analyzed in the run. |
| `model` | `gemma4:31b` | Model served by Ollama. |
| `temperature` | `0.6` | Sampling temperature (default value of the reference notebook). |
| `base_url` | `http://localhost:11434` | Ollama server address. |
| `max_iters` | `3` (multi only) | Maximum iterations of the Evaluator-Optimizer loop. |

The reported results were obtained with the default configuration of the reference notebook from the original study, which uses a sampling temperature of `0.6`; the remaining generation parameters were left at the Ollama defaults.

## Output format

In the single-agent pipeline, `output_<smell>.csv` appends to the dataset the columns `LLM`, `Test Smell`, `Date`, and `Refactored code`. In the four-agent pipeline, the CSV records the decisions per iteration (`1° - Detected smell?`, `1° - Do you agree with detection?`, `1° - Refactored code`, `1° -  LLM - Is there still a test smell?`, and analogous ones for the 2nd and 3rd iterations). Each folder also includes a `.txt` log with the full trace of the agents' responses per instance.

The `Gemma4-31B-Results.xlsx` spreadsheet consolidates the evaluation. The `Category` sheet contains the per-instance result (`True`/`False`) for both configurations, with the failure reason recorded when the result is `False`. The `Time` sheet contains the execution times per smell and configuration. The remaining sheets store the raw outputs per smell and the failure categorization.

## Evaluation criteria

The metric is **pass@1**: a smell is considered handled when the model's first attempt correctly detects and repairs it. A detection is correct when the model flags the smell and provides a consistent justification. A refactoring is correct when it (a) eliminates the target smell; (b) preserves the test's behavior; (c) remains valid under JUnit 5; and (d) introduces no new smells. Refactorings that violate any condition are recorded with the failure reason.

## Results

Pass@1 rate per smell (30 instances per type):

| Test smell | Single-agent | Four-agent |
|---|---|---|
| Assertion Roulette | 86.7% | 86.7% |
| Conditional Test Logic | 26.7% | 26.7% |
| Duplicate Assert | 86.7% | 66.7% |
| Exception Handling | 93.3% | 93.3% |
| Magic Number | 100.0% | 96.7% |
| **Overall** | **78.7%** | **74.0%** |

The single-agent pipeline solved 118 of the 150 instances (78.7%); the four-agent pipeline solved 111 (74.0%).

**RQ1.** With a single agent, Gemma-4-31B (78.7%) surpasses the proprietary models reported in the original study: o3 (74.7%), Gemini-2.5-Pro (72.0%), and Claude-4-Sonnet (59.3%). It also surpasses the best original open model (Phi-4-14B, 55.3% with two agents), the combined result of the open models (70.6%), and its direct predecessor Gemma-2-9B (40.7% in its best configuration). The single attempt of Gemma-4-31B even exceeds the pass@5 of 75.3% obtained by Phi-4-14B with four agents and up to five attempts.

**RQ2.** The four agents do not improve the result. The configurations tie on Conditional Test Logic, Assertion Roulette, and Exception Handling, and the four-agent one is worse on Magic Number (from 100.0% to 96.7%) and Duplicate Assert (from 86.7% to 66.7%). At the instance level, the single-agent pipeline solves 10 cases where the four-agent one fails, against 3 in the opposite direction, with 8 of those 10 in Duplicate Assert.

Execution time per smell:

| Test smell | Single-agent | Four-agent |
|---|---|---|
| Assertion Roulette | 18m30s | 44m38s |
| Conditional Test Logic | 1h01m41s | 44m00s |
| Duplicate Assert | 47m27s | 1h34m07s |
| Exception Handling | 25m55s | 48m38s |
| Magic Number | 18m21s | 47m00s |
| **Total** | **≈170m** | **≈277m** |

Processing the 150 instances took about 170 minutes with a single agent and about 277 minutes with four, an increase of roughly 63%.

## Failure analysis

Distribution of failure reasons per configuration:

| Failure reason | Single-agent | Four-agent |
|---|---|---|
| Behavioral change or compilation error | 22 | 32 |
| Changed the code without removing the smell | 6 | 1 |
| Invalid constructs or outside JUnit 5 | 2 | 0 |
| Neither fixed nor changed the code | 2 | 1 |
| Smell not detected | 0 | 4 |
| Correct refactoring rejected by the verifier | 0 | 1 |
| **Total failures** | **32** | **39** |

Almost all failures are concentrated in the repair stage rather than the detection stage. The single-agent pipeline never fails by missing a smell, and the four-agent one fails at that stage in only 4 cases, all caused by the additional confirmation step. The two categories exclusive to the four-agent pipeline (smell not detected and correct refactoring rejected by the verifier) indicate that the extra stages can remove correct results, an effect most visible in Duplicate Assert.

## How to cite

If this work is useful, please cite:

```bibtex
@misc{melo2026replicating,
  author       = {Rian Melo},
  title        = {Replicating Agentic Workflows for Test Smell Detection
                  and Refactoring with Gemma-4-31B},
  year         = {2026},
  howpublished = {Replication package},
  institution  = {Universidade Federal de Campina Grande (UFCG)},
  url          = {https://github.com/Rian-Ismael/Replication-Package}
}
```

Author: Rian Melo, Universidade Federal de Campina Grande (UFCG), Campina Grande, Paraíba, Brazil. Contact: rian.melo@ccc.ufcg.edu.br

Repository: https://github.com/Rian-Ismael/Replication-Package

## References

* Rian Melo et al. **Agentic LMs: Hunting Down Test Smells.** IEEE Software 43, 1 (2026), 32–40. doi:10.1109/MS.2025.3621356
* Rian Melo et al. **Agentic LMs: Hunting Down Test Smells, Replication Package.** Zenodo. doi:10.5281/zenodo.17285750
