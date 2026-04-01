"""Generator agent: implements code based on a specification."""

import json
from agents.base import BaseAgent

SYSTEM_PROMPT = """\
You are the GENERATOR agent in a multi-agent software development harness.

Your job is to implement working code based on a specification written by a PLANNER \
agent. You will receive the spec and optionally feedback from an EVALUATOR agent on \
prior iterations.

## How you work

You write code by calling the `write_file` tool for each file you need to create or \
update. You MUST use this tool — do not just output code in text.

## Guidelines
- Implement ALL features in the spec, not a subset
- Write clean, working code — not stubs or placeholders
- Include proper error handling at system boundaries
- Make the code runnable out of the box
- When you receive evaluator feedback, focus on fixing the specific issues raised
- After writing all files, output a brief CHANGELOG summarizing what you did

## On evaluator feedback iterations
When you receive feedback from a previous evaluation:
- Address every issue marked as FAIL or PARTIAL
- Do not regress on items already marked PASS
- If you disagree with feedback, explain why in your changelog
"""

WRITE_FILE_TOOL = {
    "name": "write_file",
    "description": "Write content to a file in the output directory. Use this for every file you create or modify.",
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Relative file path within the output directory (e.g., 'main.py', 'utils/helpers.py')",
            },
            "content": {
                "type": "string",
                "description": "The full file content to write",
            },
        },
        "required": ["filename", "content"],
    },
}


class GeneratorAgent(BaseAgent):
    name = "generator"
    system_prompt = SYSTEM_PROMPT

    def generate(
        self,
        spec: str,
        evaluation_feedback: str | None = None,
        iteration: int = 1,
    ) -> tuple[list[dict], str]:
        """Generate code files based on the spec and optional feedback.

        Returns:
            (files_written, changelog) where files_written is a list of
            {"filename": ..., "content": ...} dicts.
        """
        parts = [f"## Specification\n\n{spec}"]

        if evaluation_feedback:
            parts.append(
                f"## Evaluator Feedback (Iteration {iteration - 1})\n\n"
                f"Address every issue below:\n\n{evaluation_feedback}"
            )

        parts.append(
            f"\n## Instructions\n\n"
            f"This is iteration {iteration}. "
            f"Use the `write_file` tool for each file you need to create or update. "
            f"After writing all files, provide a CHANGELOG summarizing your work."
        )

        prompt = "\n\n".join(parts)
        text, tool_uses = self.call(prompt, tools=[WRITE_FILE_TOOL])

        files_written = []
        for tu in tool_uses:
            if tu["name"] == "write_file":
                files_written.append(tu["input"])

        return files_written, text
