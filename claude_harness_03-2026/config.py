"""Configuration for the agentic loop harness."""

import os
from pathlib import Path

# --- Anthropic API ---
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("HARNESS_MODEL", "claude-sonnet-4-20250514")

# --- Loop settings ---
MAX_ITERATIONS = int(os.environ.get("HARNESS_MAX_ITERATIONS", "3"))
PASS_THRESHOLD = float(os.environ.get("HARNESS_PASS_THRESHOLD", "0.8"))  # 0-1 scale

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
OUTPUT_DIR = ARTIFACTS_DIR / "output"
SPEC_PATH = ARTIFACTS_DIR / "spec.md"
EVALUATION_PATH = ARTIFACTS_DIR / "evaluation.md"
PLAN_PATH = ARTIFACTS_DIR / "plan.md"

# --- Token limits ---
MAX_TOKENS = 8192
