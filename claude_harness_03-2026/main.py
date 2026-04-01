#!/usr/bin/env python3
"""
Agentic Loop Harness — Plan, Generate, Evaluate

A three-agent system inspired by Anthropic's harness design for long-running apps.
Agents communicate through file-based handoffs in the artifacts/ directory.

Usage:
    python main.py "Build a CLI markdown-to-HTML converter with syntax highlighting"
    python main.py --task-file task.txt
    python main.py --interactive
"""

import argparse
import os
import sys
import time
from pathlib import Path

import config
from agents import PlannerAgent, GeneratorAgent, EvaluatorAgent


def log(phase: str, message: str) -> None:
    """Print a timestamped log line."""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] [{phase.upper():^10}] {message}")


def ensure_dirs() -> None:
    """Create artifact directories if they don't exist."""
    config.ARTIFACTS_DIR.mkdir(exist_ok=True)
    config.OUTPUT_DIR.mkdir(exist_ok=True)


def write_artifact(path: Path, content: str) -> None:
    """Write content to an artifact file."""
    path.write_text(content, encoding="utf-8")
    log("artifact", f"Wrote {path.relative_to(config.PROJECT_ROOT)}")


def read_artifact(path: Path) -> str | None:
    """Read an artifact file, returning None if it doesn't exist."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return None


def write_generated_files(files: list[dict]) -> dict[str, str]:
    """Write generator output files to disk. Returns filename->content map."""
    written = {}
    for f in files:
        filepath = config.OUTPUT_DIR / f["filename"]
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(f["content"], encoding="utf-8")
        written[f["filename"]] = f["content"]
        log("generator", f"  Wrote {f['filename']}")
    return written


def collect_output_files() -> dict[str, str]:
    """Read all files currently in the output directory."""
    files = {}
    for path in config.OUTPUT_DIR.rglob("*"):
        if path.is_file():
            rel = path.relative_to(config.OUTPUT_DIR)
            files[str(rel)] = path.read_text(encoding="utf-8")
    return files


def run_harness(task: str) -> None:
    """Run the full Plan → Generate → Evaluate loop."""
    ensure_dirs()

    print("=" * 70)
    print("  AGENTIC LOOP HARNESS")
    print("  Plan → Generate → Evaluate")
    print("=" * 70)
    print(f"\n  Task: {task}")
    print(f"  Model: {config.MODEL}")
    print(f"  Max iterations: {config.MAX_ITERATIONS}")
    print(f"  Pass threshold: {config.PASS_THRESHOLD}")
    print("=" * 70)

    # ------------------------------------------------------------------
    # Phase 1: PLANNING
    # ------------------------------------------------------------------
    log("planner", "Expanding task into specification...")
    planner = PlannerAgent()
    spec = planner.plan(task)
    write_artifact(config.SPEC_PATH, spec)
    log("planner", f"Specification ready ({len(spec)} chars)")
    print(f"\n{'─' * 70}")

    # ------------------------------------------------------------------
    # Phase 2-3: GENERATE → EVALUATE loop
    # ------------------------------------------------------------------
    generator = GeneratorAgent()
    evaluator = EvaluatorAgent()
    feedback = None
    final_score = 0.0

    for iteration in range(1, config.MAX_ITERATIONS + 1):
        # --- Generate ---
        log("generator", f"Iteration {iteration}/{config.MAX_ITERATIONS} — generating code...")
        files_written, changelog = generator.generate(
            spec=spec,
            evaluation_feedback=feedback,
            iteration=iteration,
        )

        if files_written:
            written_map = write_generated_files(files_written)
        else:
            log("generator", "No files produced via tool use — checking output dir")
            written_map = {}

        # Merge with any previously written files (for incremental updates)
        all_files = collect_output_files()
        all_files.update(written_map)

        if changelog:
            write_artifact(
                config.ARTIFACTS_DIR / f"changelog_iter{iteration}.md",
                changelog,
            )

        log("generator", f"Produced {len(files_written)} files, {len(all_files)} total in output/")
        print(f"\n{'─' * 70}")

        # --- Evaluate ---
        if not all_files:
            log("evaluator", "No files to evaluate — skipping")
            feedback = "No code was produced. Please generate the files using the write_file tool."
            continue

        log("evaluator", f"Evaluating iteration {iteration}...")
        score, evaluation = evaluator.evaluate(spec, all_files)
        final_score = score

        write_artifact(
            config.ARTIFACTS_DIR / f"evaluation_iter{iteration}.md",
            evaluation,
        )
        write_artifact(config.EVALUATION_PATH, evaluation)

        log("evaluator", f"Score: {score:.2f} (threshold: {config.PASS_THRESHOLD})")

        if score >= config.PASS_THRESHOLD:
            log("harness", f"PASSED at iteration {iteration} with score {score:.2f}")
            break

        log("harness", f"Below threshold — looping back to generator")
        feedback = evaluation
        print(f"\n{'─' * 70}")
    else:
        log("harness", f"Reached max iterations ({config.MAX_ITERATIONS}). Final score: {final_score:.2f}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"\n{'=' * 70}")
    print("  HARNESS COMPLETE")
    print(f"  Final score: {final_score:.2f}")
    print(f"  Output: {config.OUTPUT_DIR.relative_to(config.PROJECT_ROOT)}/")
    print(f"  Spec: {config.SPEC_PATH.relative_to(config.PROJECT_ROOT)}")
    print(f"  Evaluation: {config.EVALUATION_PATH.relative_to(config.PROJECT_ROOT)}")
    print(f"{'=' * 70}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agentic Loop Harness — Plan, Generate, Evaluate",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("task", nargs="?", help="Task description (1-4 sentences)")
    group.add_argument("--task-file", type=Path, help="Read task from a file")
    group.add_argument("--interactive", action="store_true", help="Enter task interactively")

    parser.add_argument("--model", help=f"Model to use (default: {config.MODEL})")
    parser.add_argument("--max-iterations", type=int, help=f"Max loop iterations (default: {config.MAX_ITERATIONS})")
    parser.add_argument("--threshold", type=float, help=f"Pass threshold 0-1 (default: {config.PASS_THRESHOLD})")

    args = parser.parse_args()

    if args.model:
        config.MODEL = args.model
    if args.max_iterations:
        config.MAX_ITERATIONS = args.max_iterations
    if args.threshold:
        config.PASS_THRESHOLD = args.threshold

    if args.interactive:
        print("Enter your task description (press Enter twice to submit):")
        lines = []
        while True:
            line = input()
            if line == "":
                if lines:
                    break
            else:
                lines.append(line)
        task = "\n".join(lines)
    elif args.task_file:
        task = args.task_file.read_text(encoding="utf-8").strip()
    else:
        task = args.task

    if not task:
        parser.error("Task description cannot be empty")

    run_harness(task)


if __name__ == "__main__":
    main()
