# Agentic Loop Harness

A three-agent system that implements the **Plan → Generate → Evaluate** loop described in Anthropic's [Harness Design for Long-Running Agentic Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps).

## How It Works

The harness decomposes software development into three specialized agents that communicate through file-based handoffs:

```
┌──────────┐     spec.md      ┌───────────┐    output/*     ┌───────────┐
│  PLANNER │ ───────────────► │ GENERATOR │ ──────────────► │ EVALUATOR │
│          │                  │           │ ◄────────────── │           │
└──────────┘                  └───────────┘   evaluation.md  └───────────┘
                                    ▲               │
                                    └───────────────┘
                                     feedback loop
```

### Planner Agent
Takes a brief task description (1-4 sentences) and expands it into a comprehensive product specification with features, acceptance criteria, technical requirements, and concrete success criteria for the evaluator to grade against.

### Generator Agent
Implements working code from the specification. On subsequent iterations, it receives evaluator feedback and fixes specific issues while preserving what already works. Uses tool calls to write files to the `artifacts/output/` directory.

### Evaluator Agent
Rigorously reviews the generated code against every success criterion in the spec. Fights the well-documented LLM bias toward praising its own outputs by requiring concrete evidence for every judgment. Produces a 0.00-1.00 score and actionable feedback.

The loop continues until the evaluator score exceeds the pass threshold (default: 0.80) or the maximum number of iterations is reached (default: 3).

## Key Design Principles

From the Anthropic article:

- **Separate evaluation from generation** — tuning a standalone evaluator to be skeptical is far more tractable than making a generator critical of its own work
- **File-based handoffs** — agents communicate through artifacts on disk, maintaining context across interactions
- **Concrete success criteria** — subjective goals are transformed into gradable, testable criteria
- **Iterative refinement** — the generator addresses specific evaluator feedback each round rather than starting from scratch

## Setup

### Prerequisites

- Python 3.11+
- An [Anthropic API key](https://console.anthropic.com/)

### Install

```bash
cd claude_harness_03-2026
pip install -r requirements.txt
```

### Set your API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Usage

### Basic usage

Pass a task description directly:

```bash
python main.py "Build a Python CLI tool that converts CSV files to JSON with filtering, sorting, and column selection"
```

### Read task from a file

```bash
python main.py --task-file task.txt
```

### Interactive mode

```bash
python main.py --interactive
```

### Configuration options

```bash
# Use a different model
python main.py --model claude-opus-4-20250514 "Build a ..."

# Allow more iterations (default: 3)
python main.py --max-iterations 5 "Build a ..."

# Lower the pass threshold (default: 0.80)
python main.py --threshold 0.7 "Build a ..."
```

### Environment variables

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required) | Your Anthropic API key |
| `HARNESS_MODEL` | `claude-sonnet-4-20250514` | Model to use for all agents |
| `HARNESS_MAX_ITERATIONS` | `3` | Max generate-evaluate cycles |
| `HARNESS_PASS_THRESHOLD` | `0.8` | Score (0-1) needed to pass |

## Output

After a run, the `artifacts/` directory contains:

```
artifacts/
├── spec.md                    # Full specification from the planner
├── evaluation.md              # Latest evaluation (symlink-like, always latest)
├── evaluation_iter1.md        # Evaluation from iteration 1
├── evaluation_iter2.md        # Evaluation from iteration 2 (if needed)
├── changelog_iter1.md         # Generator's changelog from iteration 1
├── changelog_iter2.md         # Generator's changelog from iteration 2
└── output/                    # Generated code files
    ├── main.py
    ├── utils.py
    └── ...
```

## Example Run

```
$ python main.py "Build a CLI markdown-to-HTML converter with syntax highlighting"

======================================================================
  AGENTIC LOOP HARNESS
  Plan → Generate → Evaluate
======================================================================

  Task: Build a CLI markdown-to-HTML converter with syntax highlighting
  Model: claude-sonnet-4-20250514
  Max iterations: 3
  Pass threshold: 0.8
======================================================================
[14:23:01] [ PLANNER  ] Expanding task into specification...
[14:23:08] [ ARTIFACT ] Wrote artifacts/spec.md
[14:23:08] [ PLANNER  ] Specification ready (2847 chars)
──────────────────────────────────────────────────────────────────────
[14:23:08] [GENERATOR ] Iteration 1/3 — generating code...
[14:23:22] [GENERATOR ]   Wrote main.py
[14:23:22] [GENERATOR ]   Wrote converter.py
[14:23:22] [GENERATOR ]   Wrote templates/base.html
[14:23:22] [GENERATOR ] Produced 3 files, 3 total in output/
──────────────────────────────────────────────────────────────────────
[14:23:22] [EVALUATOR ] Evaluating iteration 1...
[14:23:31] [EVALUATOR ] Score: 0.72 (threshold: 0.8)
[14:23:31] [ HARNESS  ] Below threshold — looping back to generator
──────────────────────────────────────────────────────────────────────
[14:23:31] [GENERATOR ] Iteration 2/3 — generating code...
[14:23:45] [GENERATOR ]   Wrote main.py
[14:23:45] [GENERATOR ]   Wrote converter.py
[14:23:45] [GENERATOR ] Produced 2 files, 3 total in output/
──────────────────────────────────────────────────────────────────────
[14:23:45] [EVALUATOR ] Evaluating iteration 2...
[14:23:53] [EVALUATOR ] Score: 0.88 (threshold: 0.8)
[14:23:53] [ HARNESS  ] PASSED at iteration 2 with score 0.88

======================================================================
  HARNESS COMPLETE
  Final score: 0.88
  Output: artifacts/output/
  Spec: artifacts/spec.md
  Evaluation: artifacts/evaluation.md
======================================================================
```

## Architecture Notes

### Why three agents instead of one?

The article's key insight: **"Separating generator from evaluator proves more tractable than making generators self-critical."** When a single agent generates and evaluates, it exhibits "confident praising" — rating mediocre output highly. A separate evaluator with explicit instructions to be skeptical produces genuinely useful feedback.

### Why file-based handoffs?

Each agent call starts with a clean context window. Passing the spec, code, and evaluation as explicit text prevents context degradation over long sessions and makes the entire process inspectable — you can read every artifact to understand exactly what each agent saw and produced.

### Adapting this harness

This is a starting point. The article suggests evolving the harness as models improve:

- **Swap in Playwright-based evaluation** for web apps (have the evaluator actually click through the UI)
- **Add sprint decomposition** for larger projects (break the spec into phases)
- **Remove components that become unnecessary** as models handle longer coherent sessions
- **Tune evaluator calibration** with few-shot examples from your domain

> "Every component in a harness encodes an assumption about what the model can't do on its own, and those assumptions are worth stress testing."
