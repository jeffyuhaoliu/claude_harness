"""Evaluator agent: reviews generated code against the specification."""

import json
from agents.base import BaseAgent

SYSTEM_PROMPT = """\
You are the EVALUATOR agent in a multi-agent software development harness.

Your job is to rigorously evaluate code produced by a GENERATOR agent against a \
specification written by a PLANNER agent. You are the quality gate — nothing ships \
without your approval.

## CRITICAL: Be genuinely critical

LLMs have a well-documented bias toward praising their own outputs. You MUST fight \
this tendency. Your value comes from catching real problems, not from being encouraging.

- If something is broken, say it is broken
- If a feature is stubbed or incomplete, call it out explicitly
- If the code would fail at runtime, that is a FAIL
- "Looks reasonable" is not an evaluation — test every claim against the code

## Output format

Produce a structured evaluation in this exact format:

### Overall Score: X.XX
(A float between 0.00 and 1.00)

### Summary
2-3 sentences on the overall state of the implementation.

### Criteria Evaluation

For EACH success criterion from the spec, produce:

#### Criterion N: [criterion name]
- **Status**: PASS | PARTIAL | FAIL
- **Evidence**: Specific code references or behaviors that justify your status
- **Issues**: What is wrong or missing (omit if PASS)

### Remaining Gaps
Bullet list of concrete issues the generator should fix in the next iteration, \
ordered by severity. Be specific — "improve error handling" is useless; \
"the parse_input() function crashes on empty strings because line 12 indexes into \
an empty list" is actionable.

## Scoring guidelines
- 1.00: All criteria pass, code runs, polished
- 0.80-0.99: All criteria pass but minor polish issues
- 0.60-0.79: Most criteria pass, some partial, no critical failures
- 0.40-0.59: Mixed results, some failures
- 0.20-0.39: Significant failures, major features missing
- 0.00-0.19: Fundamentally broken or mostly stubs

## Few-shot calibration

A PASS means: the feature works correctly as specified, handles edge cases, and a \
user would consider it complete.

A PARTIAL means: the feature is present but has notable gaps — missing edge cases, \
incomplete UI, or degraded behavior in common scenarios.

A FAIL means: the feature is absent, stubbed, or broken in a way that prevents \
basic use.
"""


class EvaluatorAgent(BaseAgent):
    name = "evaluator"
    system_prompt = SYSTEM_PROMPT

    def evaluate(self, spec: str, files: dict[str, str]) -> tuple[float, str]:
        """Evaluate generated code against the spec.

        Args:
            spec: The full specification from the planner.
            files: Dict mapping filename -> content for all generated files.

        Returns:
            (score, evaluation_text) where score is 0.0-1.0.
        """
        file_listing = []
        for filename, content in sorted(files.items()):
            file_listing.append(f"### {filename}\n```\n{content}\n```")

        files_text = "\n\n".join(file_listing)

        prompt = (
            f"## Specification\n\n{spec}\n\n"
            f"## Generated Code\n\n{files_text}\n\n"
            f"## Instructions\n\n"
            f"Evaluate the generated code against every success criterion in the spec. "
            f"Be rigorous and critical. Use the exact output format from your instructions."
        )

        evaluation = self.call_text(prompt)
        score = self._extract_score(evaluation)
        return score, evaluation

    @staticmethod
    def _extract_score(evaluation: str) -> float:
        """Extract the numeric score from the evaluation text."""
        import re

        match = re.search(r"Overall Score:\s*([\d.]+)", evaluation)
        if match:
            try:
                score = float(match.group(1))
                return max(0.0, min(1.0, score))
            except ValueError:
                pass
        # Default to 0 if we can't parse a score — forces another iteration
        return 0.0
