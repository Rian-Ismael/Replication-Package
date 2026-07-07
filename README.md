# Replicating Agentic Workflows for Test Smell Detection and Refactoring with Gemma-4-31B

Pacote de replicação do estudo de detecção e refatoração de *test smells* com pipelines agênticos, aplicado ao modelo aberto **Gemma-4-31B** servido localmente via Ollama. O trabalho reproduz o protocolo de Melo et al. (IEEE Software, 2026) substituindo o modelo por uma versão mais recente, mantendo o mesmo dataset, os mesmos prompts e os mesmos critérios de correção, sobre as mesmas 150 instâncias, e comparando um pipeline de um agente contra um de quatro agentes.

Autor: Rian Melo (UFCG, Campina Grande, PB, Brasil).

## Objetivo

O estudo responde a duas questões de pesquisa:

* **RQ1:** dentro de um pipeline agêntico, o Gemma-4-31B refatora *test smells* em nível comparável aos LLMs proprietários (o3, Claude-4-Sonnet, Gemini-2.5-Pro)?
* **RQ2:** para o Gemma-4-31B, um pipeline de quatro agentes supera o de um agente na detecção e refatoração?

Com um agente e uma única tentativa, o Gemma-4-31B refatorou corretamente 78.7% das instâncias, superando os proprietários reportados no estudo original. O pipeline de quatro agentes não apresentou ganho, empatando em três tipos de smell, apresentando desempenho inferior em dois e exigindo tempo de execução consideravelmente maior.

## Estrutura do repositório

```
.
├── Dataset/
│   ├── Dataset.xlsx                      # 150 instâncias (5 abas, uma por smell)
│   └── csv/                              # cada aba exportada como CSV (entrada dos notebooks)
├── Source Code/
│   ├── test_smell_refactor_single_agent.ipynb   # pipeline de 1 agente
│   └── test_smell_refactor_multi_agent.ipynb    # pipeline de 4 agentes
├── Outputs Gemma4-31B/
│   ├── Single/                           # saídas do pipeline de 1 agente
│   │   ├── Assertion Roulette/           # output_*.csv + agente_single_*.txt
│   │   ├── Conditional Test Logic/
│   │   ├── Duplicate Assert/
│   │   ├── Exception Handling/
│   │   └── Magic Number/
│   └── Multi/                            # saídas do pipeline de 4 agentes
│       ├── Assertion Roulette/           # output_*.csv + agentes_multi_*.txt
│       ├── Conditional Test Logic/
│       ├── Duplicate Assert/
│       ├── Exception Handling/
│       └── Magic Number/
└── Gemma4-31B-Results.xlsx              # planilha consolidada (avaliação e tempos)
```

## Dataset

O conjunto reutiliza as 150 instâncias do estudo base, extraídas de 11 sistemas Java open-source que utilizam JUnit 5: janusgraph, quarkus, testcontainers-java, opengrok, jenkins, lettuce, Mindustry, data-transfer-project, Activiti, flowable-engine e skywalking. São cinco tipos de smell, com 30 instâncias cada. Seguindo o critério do estudo original, consideram-se apenas métodos de teste com no máximo 30 linhas de código.

Definições adotadas para cada tipo de smell, conforme o estudo original:

| Smell | Definition and refactoring |
|---|---|
| **Assertion Roulette** | Occurs when a test method contains more than one assertion statement without an explanation or message (parameter in the assertion method). To mitigate this smell, developers should add a message to each assertion. |
| **Conditional Test Logic** | Arises when a test method contains one or more control statements (i.e., conditional expression, and loop statements). This can be addressed by having the developer create a dedicated test method for each condition. |
| **Duplicate Assert** | Appears when a test method contains more than one assertion statement with the same parameters. To address this, developers should split assertions that test different scenarios or states into separate tests for clarity. |
| **Exception Handling** | Occurs when a test method contains either a `throw` statement or at least a `catch` clause. To avoid this smell, use the testing framework's features (e.g., `assertThrows`) instead of manually catching or throwing exceptions. |
| **Magic Number** | Occurs when a test method contains an assertion with a numeric literal as an argument. Refactoring involves extracting and initializing all magic numbers into constants or local variables with descriptive names. |

O `Dataset.xlsx` contém uma aba por smell, com as colunas `Id`, `LLM`, `Date`, `Test Smell`, `Language`, `Project`, `URL`, `Method`, `Test Code` e `Line Count`. Os notebooks leem o dataset em formato CSV (`Dataset.csv`, via `pd.read_csv`), correspondente a um smell por vez. Para conveniência, o diretório `Dataset/csv/` já traz cada aba exportada como CSV (`Assertion_Roulette.csv`, `Conditional_Test_Logic.csv`, `Duplicate_Assert.csv`, `Exception_Handling.csv`, `Magic_Number.csv`); basta apontar o parâmetro `csv_path` para o arquivo do smell desejado (ou copiá-lo como `Dataset.csv`).

## Pipelines

Ambos os pipelines usam LangChain para orquestração e Ollama para servir o modelo. Os prompts empregam as estratégias Persona e Chain-of-Thought e são reutilizados sem modificação do estudo original.

**Um agente.** Um único agente recebe a definição do smell e o código do teste e, em uma única passagem, detecta o smell e reescreve o código. Na ausência de smell, o código original é retornado.

**Quatro agentes.** A tarefa é distribuída entre quatro agentes, com um laço Evaluator-Optimizer que repete até três vezes (`max_iters = 3`):

1. **Agente 1** detecta o smell, respondendo `YES` ou `NO` na primeira linha com justificativa.
2. **Agente 2** avalia a detecção do Agente 1; em caso de discordância, retorna `NO` com o que corrigir, e o laço de detecção reinicia com esse feedback.
3. **Agente 3** refatora o código, preservando o comportamento e mantendo validade em JUnit 5.
4. **Agente 4** verifica se o código refatorado não contém o smell, segue a especificação JUnit 5 e não introduz erros de compilação; em caso negativo, retorna `NO` com explicação, e o laço de refatoração reinicia.

A variante de dois agentes é omitida por custo, uma vez que os resultados originais a posicionavam entre as configurações de um e de quatro agentes.

## Ambiente de execução

Modelo `gemma4:31b` servido pelo Ollama e acessado pela pipeline LangChain, executado em ambiente Google Colab com GPU NVIDIA A100, usando a configuração padrão do notebook de referência do estudo original. O identificador exato do modelo está registrado no pacote.

## Reprodução

Requisitos no ambiente antes da execução: `Dataset.csv`, o arquivo de definições `test_smell_definitions_and_refactorings.txt` e um servidor Ollama acessível. O arquivo de definições segue o formato lido pela função `load_smell`:

```
test_smell_name = "Nome do Smell"
test_smell_definition = """
...definição e instruções de refatoração...
"""
```

Cada notebook expõe os seguintes parâmetros:

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `csv_path` | `Dataset.csv` | CSV com os casos de teste. |
| `definitions_path` | `test_smell_definitions_and_refactorings.txt` | Arquivo de definições dos smells. |
| `smell` | um dos cinco smells | Smell analisado na execução. |
| `model` | `gemma4:31b` | Modelo servido pelo Ollama. |
| `base_url` | `http://localhost:11434` | Endereço do servidor Ollama. |
| `max_iters` | `3` (apenas multi) | Máximo de iterações do laço Evaluator-Optimizer. |

Os resultados reportados foram obtidos com a configuração padrão do notebook de referência do estudo original.

## Formato das saídas

No pipeline de um agente, `output_<smell>.csv` acrescenta ao dataset as colunas `LLM`, `Test Smell`, `Date` e `Refactored code`. No pipeline de quatro agentes, o CSV registra as decisões por iteração (`1° - Detected smell?`, `1° - Do you agree with detection?`, `1° - Refactored code`, `1° -  LLM - Is there still a test smell?`, e análogas para a 2ª e 3ª iterações). Cada pasta inclui ainda o log `.txt` com o rastro completo das respostas dos agentes por instância.

A planilha `Gemma4-31B-Results.xlsx` consolida a avaliação. A aba `Category` contém o resultado por instância (`True`/`False`) para as duas configurações, com a razão da falha registrada quando o resultado é `False`. A aba `Time` contém os tempos de execução por smell e configuração. As demais abas armazenam os outputs brutos por smell e a categorização de falhas.

## Critérios de avaliação

A métrica é **pass@1**: o smell é considerado tratado quando a primeira tentativa do modelo o detecta e repara corretamente. Uma detecção é correta quando o modelo aponta o smell e apresenta justificativa consistente. Uma refatoração é correta quando: (a) elimina o smell alvo; (b) preserva o comportamento do teste; (c) permanece válida em JUnit 5; e (d) não introduz novos smells. Refatorações que violam qualquer condição são registradas com a razão da falha.

## Resultados

Taxa de pass@1 por smell (30 instâncias por tipo):

| Test smell | 1 agente | 4 agentes |
|---|---|---|
| Assertion Roulette | 86.7% | 86.7% |
| Conditional Test Logic | 26.7% | 26.7% |
| Duplicate Assert | 86.7% | 66.7% |
| Exception Handling | 93.3% | 93.3% |
| Magic Number | 100.0% | 96.7% |
| **Geral** | **78.7%** | **74.0%** |

O pipeline de um agente acertou 118 das 150 instâncias (78.7%); o de quatro agentes acertou 111 (74.0%).

**RQ1.** Com um agente, o Gemma-4-31B (78.7%) supera os proprietários reportados no estudo original: o3 (74.7%), Gemini-2.5-Pro (72.0%) e Claude-4-Sonnet (59.3%). Supera também o melhor modelo aberto original (Phi-4-14B, 55.3% com dois agentes), o resultado combinado dos modelos abertos (70.6%) e o antecessor direto Gemma-2-9B (40.7% na melhor configuração). A tentativa única do Gemma-4-31B ultrapassa inclusive o pass@5 de 75.3% do Phi-4-14B com quatro agentes e até cinco tentativas.

**RQ2.** Os quatro agentes não melhoram o resultado. As configurações empatam em Conditional Test Logic, Assertion Roulette e Exception Handling, e a de quatro agentes é inferior em Magic Number (de 100.0% para 96.7%) e Duplicate Assert (de 86.7% para 66.7%). No nível de instância, o pipeline de um agente acerta 10 casos em que o de quatro falha, contra 3 no sentido oposto, sendo 8 desses 10 em Duplicate Assert.

Tempo de execução por smell:

| Test smell | 1 agente | 4 agentes |
|---|---|---|
| Assertion Roulette | 18m30s | 44m38s |
| Conditional Test Logic | 1h01m41s | 44m00s |
| Duplicate Assert | 47m27s | 1h34m07s |
| Exception Handling | 25m55s | 48m38s |
| Magic Number | 18m21s | 47m00s |
| **Total** | **≈170m** | **≈277m** |

O processamento das 150 instâncias levou cerca de 170 minutos com um agente e cerca de 277 minutos com quatro, um aumento de aproximadamente 63%.

## Análise de falhas

Distribuição das razões de falha por configuração:

| Razão da falha | 1 agente | 4 agentes |
|---|---|---|
| Mudança de comportamento ou erro de compilação | 22 | 32 |
| Alterou o código sem remover o smell | 6 | 1 |
| Construções inválidas ou fora de JUnit 5 | 2 | 0 |
| Não corrigiu nem alterou o código | 2 | 1 |
| Smell não detectado | 0 | 4 |
| Refatoração correta rejeitada pelo verificador | 0 | 1 |
| **Total de falhas** | **32** | **39** |

A quase totalidade das falhas concentra-se na etapa de reparo, e não na de detecção. O pipeline de um agente nunca falha por não identificar um smell, e o de quatro falha nessa etapa apenas em 4 casos, todos decorrentes da confirmação adicional. As duas categorias exclusivas do pipeline de quatro agentes (smell não detectado e refatoração correta rejeitada pelo verificador) indicam que os estágios adicionais podem remover resultados corretos, efeito mais evidente em Duplicate Assert.

## Como citar

Se este trabalho for útil, cite:

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

Autor: Rian Melo, Universidade Federal de Campina Grande (UFCG), Campina Grande, Paraíba, Brasil. Contato: rian.melo@ccc.ufcg.edu.br

Repositório: https://github.com/Rian-Ismael/Replication-Package

## Referências

* Rian Melo et al. **Agentic LMs: Hunting Down Test Smells.** IEEE Software 43, 1 (2026), 32 a 40. doi:10.1109/MS.2025.3621356
* Rian Melo et al. **Agentic LMs: Hunting Down Test Smells, Replication Package.** Zenodo. doi:10.5281/zenodo.17285750
