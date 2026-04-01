"""Base agent class wrapping the Anthropic API."""

import json
import anthropic
import config


class BaseAgent:
    """Base class for all agents in the harness.

    Each agent has a role-specific system prompt and communicates
    through structured messages via the Claude API.
    """

    name: str = "base"
    system_prompt: str = "You are a helpful assistant."

    def __init__(self, model: str | None = None):
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = model or config.MODEL

    def call(self, user_message: str, tools: list[dict] | None = None) -> str:
        """Send a message to the Claude API and return the text response."""
        kwargs = {
            "model": self.model,
            "max_tokens": config.MAX_TOKENS,
            "system": self.system_prompt,
            "messages": [{"role": "user", "content": user_message}],
        }
        if tools:
            kwargs["tools"] = tools

        response = self.client.messages.create(**kwargs)

        # Extract text blocks from the response
        text_parts = []
        tool_uses = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_uses.append({"name": block.name, "input": block.input})

        return "\n".join(text_parts), tool_uses

    def call_text(self, user_message: str) -> str:
        """Convenience: call and return only the text portion."""
        text, _ = self.call(user_message)
        return text
