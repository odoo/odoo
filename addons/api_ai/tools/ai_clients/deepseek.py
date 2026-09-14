import json
import logging

from .openai_compatible import OpenAICompatibleClient
from odoo.addons.integration.tools.exceptions import CommError

_logger = logging.getLogger(__name__)


class DeepSeekClient(OpenAICompatibleClient):
    ENDPOINT_CODE = "deepseek"

    REASONING_MODEL = "deepseek-flash"

    MAX_TOKENS_LIMIT = 393216

    def structured_output(
        self,
        prompt,
        schema,
        tool_name="extract_data",
        tool_description="Extract structured data from the input",
        model=None,
        **kwargs,
    ):
        result = self.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": tool_description,
                        "parameters": schema,
                    },
                },
            ],
            tool_choice={"type": "function", "function": {"name": tool_name}},
            **kwargs,
        )
        for call in self._get_tool_calls(result):
            function = call.get("function") or {}
            if function.get("name") == tool_name:
                return self._get_tool_arguments(function)
        raise CommError(f"DeepSeek answered without calling {tool_name!r}")

    def reasoning_completion(self, prompt, max_tokens=5000, model=None, **kwargs):
        model = model or self.REASONING_MODEL
        result = self.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=max_tokens,
            **{"thinking": {"type": "enabled"}, **kwargs},
        )
        choices = result.get("choices") or [{}]
        return {
            "content": (choices[0].get("message") or {}).get("content") or "",
            "usage": self.get_usage(result),
            "model": result.get("model", model),
        }

    def tool_conversation(
        self,
        prompt,
        tools,
        tool_executor,
        max_turns=10,
        model=None,
        **kwargs,
    ):
        messages = [{"role": "user", "content": prompt}]
        conversation_history = []
        result = {}

        for turn in range(max_turns):
            result = self.chat_completion(
                messages=messages, model=model, tools=tools, **kwargs
            )
            if not result.get("choices"):
                break

            message = result["choices"][0].get("message") or {}
            messages.append(message)
            conversation_history.append(message)

            tool_calls = self._get_tool_calls(result)
            if not tool_calls:
                return {
                    "content": message.get("content", ""),
                    "conversation_history": conversation_history,
                    "turns": turn + 1,
                    "usage": self.get_usage(result),
                }

            for tool_call in tool_calls:
                function = tool_call.get("function") or {}
                try:
                    content = tool_executor(
                        function.get("name", ""), self._get_tool_arguments(function)
                    )
                except Exception as error:
                    _logger.exception("Tool %s failed", function.get("name"))
                    content = {"error": str(error)}
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "content": json.dumps(content),
                    },
                )

        return {
            "content": "Maximum conversation turns reached",
            "conversation_history": conversation_history,
            "turns": max_turns,
            "usage": self.get_usage(result),
        }

    @staticmethod
    def _get_tool_calls(result):
        choices = result.get("choices") or [{}]
        return (choices[0].get("message") or {}).get("tool_calls") or []

    @staticmethod
    def _get_tool_arguments(function):
        try:
            return json.loads(function.get("arguments") or "{}")
        except json.JSONDecodeError as error:
            raise CommError(
                f"DeepSeek called {function.get('name')!r} with arguments that "
                f"are not JSON: {error}",
            ) from error


def get_deepseek_client(env, company_id=None):
    return DeepSeekClient(env, company_id)
