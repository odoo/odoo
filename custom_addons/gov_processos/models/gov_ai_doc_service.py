import json
import logging
import re
import time
import urllib.error
import urllib.request

from markupsafe import escape

from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class GovAiDocService:
    """Serviço de geração de conteúdo IA com múltiplos provedores."""

    _PLACEHOLDER_RE = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")

    @classmethod
    def render_placeholders(cls, text, context):
        if not text:
            return ""
        data = context or {}

        def _replace(match):
            key = match.group(1)
            value = data.get(key, "")
            if value is None:
                return ""
            if isinstance(value, (list, dict)):
                return json.dumps(value, ensure_ascii=False)
            return str(value)

        return cls._PLACEHOLDER_RE.sub(_replace, text)

    @classmethod
    def build_memory_block(cls, memory_records):
        if not memory_records:
            return ""
        lines = []
        for rec in memory_records:
            snippet = (rec.content_text or "").strip()
            if len(snippet) > 1400:
                snippet = snippet[:1400] + "..."
            lines.append(f"- {rec.name or 'Memoria'}:\n{snippet}")
        return "\n\n".join(lines)

    @classmethod
    def _http_post_json(cls, url, payload, headers, timeout_seconds):
        raw_payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url=url,
            data=raw_payload,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8", errors="replace")
                return json.loads(body), body
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise UserError(
                f"Falha HTTP {exc.code} no provedor IA. Resposta: {body[:600]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise UserError(f"Não foi possível conectar ao provedor IA: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise UserError("Resposta do provedor IA não está em JSON válido.") from exc

    @classmethod
    def _generate_openai(cls, config, system_prompt, user_prompt):
        api_key = (config.api_key or "").strip()
        if not api_key:
            raise UserError("API key OpenAI não configurada.")
        endpoint = (config.endpoint_url or "").strip() or "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": config.model_name or "gpt-4o-mini",
            "temperature": config.temperature,
            "max_tokens": int(config.max_tokens or 2000),
            "messages": [
                {"role": "system", "content": system_prompt or ""},
                {"role": "user", "content": user_prompt or ""},
            ],
        }
        response_json, raw_response = cls._http_post_json(
            endpoint,
            payload,
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            int(config.timeout_seconds or 60),
        )
        text = (
            response_json.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not text:
            raise UserError("OpenAI retornou resposta vazia.")
        return text, raw_response

    @classmethod
    def _generate_anthropic(cls, config, system_prompt, user_prompt):
        api_key = (config.api_key or "").strip()
        if not api_key:
            raise UserError("API key Anthropic não configurada.")
        endpoint = (config.endpoint_url or "").strip() or "https://api.anthropic.com/v1/messages"
        payload = {
            "model": config.model_name or "claude-3-5-sonnet-latest",
            "max_tokens": int(config.max_tokens or 2000),
            "temperature": config.temperature,
            "system": system_prompt or "",
            "messages": [{"role": "user", "content": user_prompt or ""}],
        }
        response_json, raw_response = cls._http_post_json(
            endpoint,
            payload,
            {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            int(config.timeout_seconds or 60),
        )
        chunks = response_json.get("content") or []
        parts = [chunk.get("text", "") for chunk in chunks if chunk.get("type") == "text"]
        text = "\n".join(parts).strip()
        if not text:
            raise UserError("Anthropic retornou resposta vazia.")
        return text, raw_response

    @classmethod
    def _generate_huggingface(cls, config, system_prompt, user_prompt):
        api_key = (config.api_key or "").strip()
        if not api_key:
            raise UserError("API key Hugging Face não configurada.")

        model_name = (config.model_name or "").strip()
        if not model_name:
            raise UserError("Modelo Hugging Face não configurado.")

        try:
            from langchain_core.messages import HumanMessage, SystemMessage
            from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
        except Exception as exc:
            raise UserError(
                "Provider Hugging Face requer LangChain: instale "
                "'langchain-huggingface' e 'langchain-core'."
            ) from exc

        endpoint = (config.endpoint_url or "").strip()
        endpoint_kwargs = {}
        if endpoint and endpoint.startswith("http"):
            if endpoint.endswith("/models"):
                endpoint_kwargs["endpoint_url"] = f"{endpoint.rstrip('/')}/{model_name}"
            else:
                endpoint_kwargs["endpoint_url"] = endpoint

        llm = HuggingFaceEndpoint(
            repo_id=model_name,
            huggingfacehub_api_token=api_key,
            temperature=config.temperature,
            max_new_tokens=int(config.max_tokens or 2000),
            timeout=int(config.timeout_seconds or 90),
            **endpoint_kwargs,
        )

        messages = [
            SystemMessage(content=system_prompt or ""),
            HumanMessage(content=user_prompt or ""),
        ]

        raw_response = ""
        text = ""
        try:
            chat = ChatHuggingFace(llm=llm)
            result = chat.invoke(messages)
            raw_response = str(getattr(result, "response_metadata", "") or "")
            text = (getattr(result, "content", "") or "").strip()
        except Exception:
            # Fallback de compatibilidade para versões sem ChatHuggingFace.
            prompt = (system_prompt or "").strip()
            if prompt:
                prompt += "\n\n"
            prompt += user_prompt or ""
            result = llm.invoke(prompt)
            text = (result or "").strip() if isinstance(result, str) else str(result).strip()
            raw_response = str(result)

        if not text:
            raise UserError("Hugging Face retornou resposta vazia.")
        return text, raw_response

    @classmethod
    def _generate_ollama(cls, config, system_prompt, user_prompt):
        import os
        ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434").rstrip("/")
        endpoint = (config.endpoint_url or "").strip() or f"{ollama_host}/api/generate"
        prompt = (system_prompt or "").strip()
        if prompt:
            prompt += "\n\n"
        prompt += user_prompt or ""
        timeout = int(config.timeout_seconds or 120)

        primary_model = (config.model_name or "llama3.2:1b").strip()
        fallback_models = []
        if getattr(config, "env", None):
            fallback_raw = (
                config.env["ir.config_parameter"].sudo().get_param("gov_ai_ml.ollama_fallback_models")
                or "qwen3.5:0.8b,llama3.2:1b"
            )
            fallback_models = [
                model.strip()
                for model in fallback_raw.split(",")
                if model.strip() and model.strip() != primary_model
            ]

        attempts = [primary_model] + fallback_models
        errors = []
        for model in attempts:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": config.temperature,
                },
            }
            try:
                response_json, raw_response = cls._http_post_json(
                    endpoint,
                    payload,
                    {"Content-Type": "application/json"},
                    timeout,
                )
                text = (response_json.get("response") or "").strip()
                if text:
                    return text, raw_response, model
                errors.append(f"{model}: resposta vazia")
            except UserError as exc:
                errors.append(f"{model}: {str(exc)}")

        raise UserError("Falha no Ollama para todos os modelos: " + " | ".join(errors[:3]))

    @classmethod
    def _generate_odoo_chat(cls, template, context, user_prompt):
        # Fallback interno sem chamadas externas: gera rascunho consistente.
        if template and template.output_format == "latex":
            seed = template.latex_template or template.latex_source or ""
            if seed:
                return cls.render_placeholders(seed, context), "odoo_chat_local_latex"
        if template and template.output_format == "typst":
            seed = template.typst_template or template.source_native_text or ""
            if seed:
                return cls.render_placeholders(seed, context), "odoo_chat_local_typst"
        rendered = cls.render_placeholders(user_prompt, context)
        html = (
            "<h3>Rascunho IA (Odoo Chat Interno)</h3>"
            "<p>Documento gerado localmente sem API externa.</p>"
            "<h4>Base do Prompt</h4>"
            f"<pre style='white-space:pre-wrap'>{escape(rendered)}</pre>"
        )
        return html, "odoo_chat_local_html"

    @classmethod
    def generate_text(
        cls,
        config,
        system_prompt,
        user_prompt,
        template=None,
        context=None,
    ):
        provider = config.provider if config else "odoo_chat"
        model_name = config.model_name if config and config.model_name else ""
        start = time.time()
        raw_response = ""

        if provider == "openai":
            text, raw_response = cls._generate_openai(config, system_prompt, user_prompt)
        elif provider == "anthropic":
            text, raw_response = cls._generate_anthropic(config, system_prompt, user_prompt)
        elif provider == "huggingface":
            text, raw_response = cls._generate_huggingface(config, system_prompt, user_prompt)
        elif provider == "ollama":
            text, raw_response, used_model = cls._generate_ollama(config, system_prompt, user_prompt)
            model_name = used_model or model_name
        else:
            text, raw_response = cls._generate_odoo_chat(template, context, user_prompt)
            if not model_name:
                model_name = "odoo_chat_local"

        duration_ms = int((time.time() - start) * 1000)
        _logger.info("IA geração concluída provider=%s model=%s duration_ms=%s", provider, model_name, duration_ms)
        return {
            "provider": provider,
            "model_name": model_name,
            "text": text,
            "raw_response": raw_response,
            "duration_ms": duration_ms,
        }
