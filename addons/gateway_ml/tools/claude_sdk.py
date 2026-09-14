import asyncio
import logging
import os
from pathlib import Path

from odoo.exceptions import UserError
from odoo.tools import config as odoo_config

from .ai_clients.claude import ClaudeClient

_logger = logging.getLogger(__name__)

_ENDPOINT_CODE = "claude"

_WORKDIR_PARAM = "gateway_ml.claude_workdir"
_LEGACY_WORKDIR_PARAM = "ai_claude.base_workdir"


def get_claude_api_token(env):
    credential = env["credential.credential"]._get_for_endpoint_code(_ENDPOINT_CODE)
    api_key = credential and credential._use_secret("env:claude_sdk", prefer="api_key")
    if not api_key:
        raise UserError(
            env._(
                "No Claude API credential is configured for %(company)s. "
                "Add one against the Claude service in Integrations → "
                "Credentials.",
                company=env.company.display_name,
            )
        )
    return api_key


try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        ToolUseBlock,
        query,
    )

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    query = None
    AssistantMessage = ResultMessage = TextBlock = ToolUseBlock = None


def _default_base_dir(env):
    base_param = None
    if env is not None:
        params = env["ir.config_parameter"].sudo()
        base_param = params.get_param(_WORKDIR_PARAM) or params.get_param(
            _LEGACY_WORKDIR_PARAM
        )
    return base_param or f"{odoo_config['data_dir']}/gateway_ml/claude"


def _default_model(env):
    if env is not None:
        provider = (
            env["gateway.ml.provider"]
            .sudo()
            .search([("code", "=", _ENDPOINT_CODE)], limit=1)
        )
        if provider.default_model_id.active and provider.default_model_id.code:
            return provider.default_model_id.code
        chat = provider.service_ids.filtered(lambda row: row.operation == "chat")
        if chat.model_id.code:
            return chat.model_id.code
    return ClaudeClient.FALLBACK_MODEL


def _resolve_work_dir(env, work_dir: str, base_dir: str | None = None):
    base_str = base_dir or _default_base_dir(env)
    base = Path(base_str).resolve()
    base.mkdir(parents=True, exist_ok=True)

    user_path = Path(work_dir)
    if user_path.is_absolute():
        raise UserError(  # pylint: disable=missing-gettext,E8507
            f"work_dir must be relative to the Claude work-dir root at {base} "
            f"(got absolute path: {work_dir!r})"
        )

    resolved = (base / user_path).resolve()
    if not resolved.is_relative_to(base):
        raise UserError(  # pylint: disable=missing-gettext,E8507
            f"work_dir {work_dir!r} escapes the Claude work-dir root at {base}"
        )

    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


class ClaudeSDKClient:
    def __init__(
        self,
        work_dir: str,
        system_prompt: str = "",
        model: str | None = None,
        max_turns: int = 50,
        allowed_tools: list | None = None,
        permission_mode: str = "default",
        env=None,
        base_dir: str | None = None,
        api_key: str | None = None,
    ):
        if not SDK_AVAILABLE:
            raise UserError(  # pylint: disable=missing-gettext,E8507
                "Claude Agent SDK not installed. "
                "Install with: pip install claude-agent-sdk\n"
                "Also requires: npm install -g @anthropic-ai/claude-code"
            )

        self.work_dir = _resolve_work_dir(env, work_dir, base_dir)

        model = model or _default_model(env)
        self.model = model
        self.max_turns = max_turns
        self.system_prompt = system_prompt
        self.permission_mode = permission_mode

        if allowed_tools is None:
            allowed_tools = ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]

        self.allowed_tools = allowed_tools

        self.stderr_lines = []

        def stderr_callback(line: str):
            self.stderr_lines.append(line)
            _logger.error("[Node.js stderr] %s", line)

        node_env = {
            **os.environ,
            "NODE_OPTIONS": "--max-old-space-size=8192",
        }
        if api_key:
            node_env["ANTHROPIC_API_KEY"] = api_key

        self.options = ClaudeAgentOptions(
            allowed_tools=allowed_tools,
            permission_mode=permission_mode,
            model=model,
            max_turns=max_turns,
            cwd=str(self.work_dir),
            stderr=stderr_callback,
            env=node_env,
            system_prompt=system_prompt or None,
        )

        _logger.info(
            "ClaudeSDKClient initialized: work_dir=%s, model=%s, max_turns=%s, tools=%s",
            self.work_dir,
            model,
            max_turns,
            allowed_tools,
        )

    async def execute_async(self, prompt: str) -> dict:
        messages = []
        result_data = {
            "success": False,
            "messages": [],
            "result": "",
            "usage": {},
            "cost_usd": 0,
            "num_turns": 0,
        }

        try:
            _logger.info("Starting query() with SDK...")
            async for message in query(prompt=prompt, options=self.options):
                messages.append(message)

                if isinstance(message, AssistantMessage):
                    for block in getattr(message, "content", []):
                        if isinstance(block, TextBlock):
                            text = getattr(block, "text", "")
                            text_preview = text[:100] if len(text) > 100 else text
                            _logger.debug("Claude: %s...", text_preview)
                        elif isinstance(block, ToolUseBlock):
                            _logger.info(
                                "Tool use: %s",
                                getattr(block, "name", "unknown"),
                            )

                if isinstance(message, ResultMessage):
                    result_data = {
                        "success": not getattr(message, "is_error", False),
                        "result": getattr(message, "result", "") or "",
                        "num_turns": getattr(message, "num_turns", 0),
                        "cost_usd": getattr(message, "total_cost_usd", 0) or 0,
                        "usage": getattr(message, "usage", {}) or {},
                        "duration_ms": getattr(message, "duration_ms", 0),
                        "session_id": getattr(message, "session_id", ""),
                    }

            result_data["messages"] = messages
            return result_data

        except Exception as e:
            error_str = str(e).lower()

            _logger.error("SDK Execution Error: %s", type(e).__name__)
            _logger.error("Error message: %s", e)

            if self.stderr_lines:
                _logger.error("Captured stderr lines from Node.js:")
                for line in self.stderr_lines:
                    _logger.error("  %s", line)

            if "cli not found" in error_str or "command not found" in error_str:
                error_msg = "Claude Code CLI not found. Install with: npm install -g @anthropic-ai/claude-code"
            elif "connection" in error_str or "connect" in error_str:
                error_msg = f"Failed to connect to Claude Code: {e}"
            elif hasattr(e, "exit_code"):
                error_msg = f"Process error (exit {e.exit_code}): {getattr(e, 'stderr', str(e))}"
            else:
                error_msg = f"Claude SDK error: {e}"

            _logger.error("Final error: %s", error_msg)
            raise UserError(error_msg) from e  # pylint: disable=missing-gettext,E8507

    def execute(self, prompt: str) -> dict:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.execute_async(prompt))
        raise RuntimeError(
            "ClaudeSDKClient.execute blocks, and this thread already runs an event "
            "loop; await execute_async instead"
        )
