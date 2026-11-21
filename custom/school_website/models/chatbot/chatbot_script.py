# -*- coding: utf-8 -*-

import logging
import os
import re
import requests
from odoo import _, api, fields, models
from odoo.tools import config, email_normalize, html2plaintext

_logger = logging.getLogger(__name__)


class ChatbotScript(models.Model):
    _inherit = "chatbot.script"

    use_ai = fields.Boolean(
        string="Enable AI Intelligence",
        default=False,
        help="When enabled, visitor queries will be processed and answered using an AI Large Language Model (OpenAI or Google Gemini).",
    )
    ai_provider = fields.Selection(
        [
            ("openai", "OpenAI (ChatGPT)"),
            ("gemini", "Google Gemini"),
            ("openrouter", "OpenRouter (OpenRouter.ai)"),
        ],
        string="AI Provider",
        default="openai",
        help="Select AI provider to power this chatbot.",
    )
    ai_api_key = fields.Char(
        string="API Key",
        help="Custom API key for this bot. If left blank, the bot will read 'api_key' from odoo.conf, environment variable API_KEY, or Website Settings.",
    )
    ai_model = fields.Char(
        string="AI Model",
        default="gpt-4o-mini",
        help="Model identifier, e.g. 'gpt-4o-mini', 'gpt-4o', 'gemini-1.5-flash', or 'gemini-1.5-pro'.",
    )
    ai_temperature = fields.Float(
        string="Temperature",
        default=0.7,
        help="Creativity temperature between 0.0 (focused) and 1.0 (creative). Default is 0.7.",
    )
    ai_system_prompt = fields.Text(
        string="System Prompt",
        default=(
            "You are Harvard University's official conversational AI assistant. "
            "Help prospective students, applicants, and visitors with inquiries regarding undergraduate "
            "and graduate academic programs, admission requirements, deadlines, tuition, scholarships, "
            "campus life, and upcoming campus events. Answer concisely, politely, and authoritatively. "
            "Keep replies brief (2-4 sentences or compact bullet points) so they fit nicely into live chat."
        ),
        help="Personality and knowledge prompt passed to the AI model on every conversation turn.",
    )
    ai_fallback_on_no_operator = fields.Boolean(
        string="AI Fallback on Operator Offline",
        default=True,
        help="If no human operators are online to take over the chat, allow AI to answer the visitor.",
    )

    @api.depends("script_step_ids.is_forward_operator", "script_step_ids.step_type")
    def _compute_first_step_warning(self):
        super()._compute_first_step_warning()
        for script in self:
            welcome_steps = script.script_step_ids and script._get_welcome_steps()
            if welcome_steps and welcome_steps[-1].step_type == "ai_chat":
                script.first_step_warning = False

    def _to_store_defaults(self, target):
        return super()._to_store_defaults(target) + ["use_ai"]

    def action_test_ai_connection(self):
        """Action button to test whether the configured AI API credentials work."""
        self.ensure_one()
        test_prompt = "Say hello in 5 words."
        provider = self.ai_provider or "openai"
        try:
            reply = self._generate_ai_response(test_prompt)
            if "Service Notice: Error" in reply or "AI response unavailable" in reply:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("AI Connection Failed"),
                        "message": html2plaintext(reply),
                        "type": "danger",
                        "sticky": True,
                    },
                }
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("AI Connection Successful!"),
                    "message": _("Successfully connected to %s (%s). Test response: %s")
                    % (provider.upper(), self.ai_model or "default", html2plaintext(reply)),
                    "type": "success",
                    "sticky": False,
                },
            }
        except Exception as e:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Connection Error"),
                    "message": str(e),
                    "type": "danger",
                    "sticky": True,
                },
            }

    def _validate_email(self, email_address, discuss_channel):
        """
        Intelligent email validation for AI-enabled chatbot:
        - If input is a valid email: normalize and proceed with standard flow.
        - If input is NOT an email and AI is enabled: treat the visitor's input as an AI prompt/question,
          generate the intelligent AI response with real database knowledge, and return it in posted_message
          so the visitor gets an immediate, helpful answer without being trapped in an email validation loop.
        """
        clean_text = html2plaintext(email_address or "").strip()
        email_normalized = email_normalize(clean_text)

        # Allow user to write phrases containing an email (e.g. "my email is user@example.com")
        if not email_normalized:
            match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", clean_text)
            if match:
                email_normalized = email_normalize(match.group(0))

        posted_message = False
        error_message = False

        if email_normalized:
            if self.use_ai:
                confirmation = _(
                    "<p>Thank you! We've noted your email: <strong>%s</strong>. "
                    "An admissions counselor will follow up with you. "
                    "Feel free to ask any other questions you may have!</p>"
                ) % email_normalized
                posted_message = discuss_channel._chatbot_post_message(self, confirmation)
            return {
                "success": True,
                "posted_message": posted_message,
                "error_message": False,
            }

        # User entered a query / question rather than an email address
        if self.use_ai:
            ai_reply = self._generate_ai_response(clean_text, channel=discuss_channel)
            posted_message = discuss_channel._chatbot_post_message(self, ai_reply)
        else:
            error_message = self.env._(
                "'%(input_email)s' does not look like a valid email. Can you please try again?",
                input_email=clean_text,
            )
            posted_message = discuss_channel._chatbot_post_message(self, error_message)

        return {
            "success": False,
            "posted_message": posted_message,
            "error_message": error_message,
        }

    def _resolve_ai_credentials(self):
        """
        Resolve API key, provider, and model following the priority order:
        1. Explicitly configured on this chatbot record (ai_api_key)
        2. Configured in odoo.conf (key name: 'api_key' or 'chatbot_api_key')
        3. Environment variable (API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY)
        4. Stored in ir.config_parameter (school_website.chatbot_ai_api_key)
        """
        self.ensure_one()
        ICP = self.env["ir.config_parameter"].sudo()

        # 1. Resolve API key
        conf_api_key = (config.get("api_key") or config.options.get("api_key") or config.get("chatbot_api_key") or "").strip()
        env_api_key = (os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY") or "").strip()
        db_api_key = (ICP.get_param("school_website.chatbot_ai_api_key", "") or "").strip()
        record_api_key = (self.ai_api_key or "").strip()

        api_key = record_api_key or conf_api_key or env_api_key or db_api_key

        # 2. Resolve Provider
        if api_key.startswith("sk-or-"):
            provider = "openrouter"
        elif self.ai_provider and self.ai_provider in ("gemini", "openrouter"):
            provider = self.ai_provider
        else:
            provider = ICP.get_param("school_website.chatbot_ai_provider", "") or config.get("ai_provider") or self.ai_provider
            if not provider or provider == "openai":
                if api_key.startswith(("AQ.", "AIza")):
                    provider = "gemini"
                else:
                    provider = "openai"

        # 3. Resolve Model
        model = (self.ai_model or "").strip() or (config.get("ai_model") or "").strip() or (ICP.get_param("school_website.chatbot_ai_model", "") or "").strip()
        if "liquid" in model.lower() or "lfm" in model.lower():
            provider = "openrouter"
            if ":free" not in model:
                model = "liquid/lfm-2.5-2.6b:free"
        elif provider == "openrouter":
            if not model:
                model = "liquid/lfm-2.5-2.6b:free"
            elif "/" not in model:
                model = f"openai/{model}"
        elif provider == "gemini" and (not model or model == "gpt-4o-mini"):
            model = "gemini-1.5-flash"
        elif provider == "openai" and (not model or "gemini" in model):
            model = "gpt-4o-mini"
        elif not model:
            model = "gpt-4o-mini"

        # 4. Resolve System Prompt
        system_prompt = self.ai_system_prompt or ICP.get_param(
            "school_website.chatbot_ai_system_prompt",
            "You are Harvard University's official conversational AI assistant."
        )

        return {
            "api_key": api_key,
            "provider": provider,
            "model": model,
            "system_prompt": system_prompt,
        }

    def _get_university_knowledge_context(self, user_query=""):
        """
        Dynamically gather official Harvard University system data from Odoo database:
        programs, faculties/departments, subjects/curriculum, credit requirements, notices, and portal URLs.
        Provides real-time knowledge augmentation (RAG) to the LLM so the chatbot has
        100% accurate, up-to-date knowledge about this project.
        """
        env = self.env
        knowledge_lines = ["\n[OFFICIAL UNIVERSITY REAL-TIME DATABASE KNOWLEDGE]"]

        # 1. Degree Programs
        if "university.program" in env:
            programs = env["university.program"].sudo().search([("active", "=", True)])
            if programs:
                knowledge_lines.append(f"Academic Degree Programs Offered ({len(programs)} degrees):")
                for p in programs:
                    dept = p.department_id.name if p.department_id else "General"
                    knowledge_lines.append(
                        f"  - {p.name} ({p.degree_type}) [Code: {p.code or 'N/A'}, Credits: {p.total_credits}, Dept: {dept}]"
                    )

        # 2. Departments & Subject Overview
        if "university.department" in env:
            depts = env["university.department"].sudo().search([])
            if depts:
                dept_summaries = []
                for d in depts:
                    sub_count = (
                        env["university.subject"].sudo().search_count([("department_id", "=", d.id)])
                        if "university.subject" in env
                        else 0
                    )
                    dept_summaries.append(f"{d.name} ({sub_count} subjects)")
                knowledge_lines.append(f"Departments ({len(depts)}): " + ", ".join(dept_summaries))

        # 3. Subjects / Curriculum (Relevant or Department-specific)
        if "university.subject" in env:
            query_lower = (user_query or "").lower()

            # Check if user asked about a specific department
            matched_dept = None
            if "university.department" in env and query_lower:
                for d in env["university.department"].sudo().search([]):
                    keywords = [w for w in d.name.lower().split() if len(w) > 3 and w not in ("department", "school")]
                    if any(kw in query_lower for kw in keywords):
                        matched_dept = d
                        break

            if matched_dept:
                subject_domain = [("department_id", "=", matched_dept.id)]
                total_dept_subs = env["university.subject"].sudo().search_count(subject_domain)
                subjects = env["university.subject"].sudo().search(subject_domain, limit=25)
                knowledge_lines.append(f"Subjects taught in {matched_dept.name} (Total: {total_dept_subs} subjects):")
                for s in subjects:
                    code_str = f" [Code: {s.code}]" if getattr(s, "code", None) else ""
                    cr_str = f" ({s.credits} credits)" if getattr(s, "credits", None) else ""
                    knowledge_lines.append(f"  * {s.name}{code_str}{cr_str}")
            elif any(w in query_lower for w in ("subject", "course", "learn", "study", "curriculum", "class")):
                knowledge_lines.append("Key Academic Subjects Offered Across Departments:")
                subjects = env["university.subject"].sudo().search([], limit=30)
                for s in subjects:
                    dept_name = s.department_id.name if getattr(s, "department_id", None) else "General"
                    knowledge_lines.append(f"  * {s.name} ({dept_name}, {getattr(s, 'credits', 3)} credits)")

        # 4. Notice Board & Announcements
        if "university.notice.board" in env:
            notices = env["university.notice.board"].sudo().search([("active", "=", True)], order="id desc", limit=4)
            if notices:
                knowledge_lines.append("Latest Announcements & Notices:")
                for n in notices:
                    tag = (n.notice_type or "Notice").upper()
                    knowledge_lines.append(f"  - [{tag}] {n.name}")

        # 5. Official Portal Navigation
        knowledge_lines.append("Official Website Links to direct visitors:")
        knowledge_lines.append("  - Course Directory: /courses")
        knowledge_lines.append("  - Online Admissions Application: /admission/apply")
        knowledge_lines.append("  - Campus Events & Notices: /events")
        knowledge_lines.append("  - Jobs & Careers: /jobs")
        knowledge_lines.append("  - Contact & Admissions Office: /contactus")
        knowledge_lines.append("[END OF UNIVERSITY DATABASE KNOWLEDGE]\n")

        return "\n".join(knowledge_lines)

    def _generate_ai_response(self, user_prompt, channel=None, history_limit=6):
        """
        Generate an intelligent AI response using OpenAI or Google Gemini.
        :param user_prompt: string question or statement from visitor
        :param channel: optional discuss.channel record to pull recent conversation history
        :param history_limit: maximum number of recent messages to include as chat context
        :return: HTML string formatted for display in livechat bubble
        """
        self.ensure_one()
        creds = self._resolve_ai_credentials()
        api_key = creds["api_key"]
        provider = creds["provider"]
        model = creds["model"]
        base_prompt = creds["system_prompt"]

        # Augment with real-time university database knowledge
        knowledge_context = self._get_university_knowledge_context(user_prompt)
        system_prompt = f"{base_prompt}\n\n{knowledge_context}"

        if not api_key:
            return _(
                "<p><em>AI response unavailable: No API key found. "
                "You can define 'api_key = ...' in odoo.conf, set an environment variable API_KEY, "
                "or configure it in Chatbot settings.</em></p>"
            )

        # Build chronological conversation context if channel is provided
        history = []
        if channel:
            bot_partner_id = self.operator_partner_id.id
            recent_messages = self.env["mail.message"].sudo().search(
                [
                    ("model", "=", "discuss.channel"),
                    ("res_id", "=", channel.id),
                    ("message_type", "in", ("comment", "notification")),
                ],
                order="id desc",
                limit=history_limit,
            )
            for msg in reversed(recent_messages):
                clean_body = html2plaintext(msg.body or "").strip()
                if not clean_body:
                    continue
                role = "assistant" if msg.author_id.id == bot_partner_id else "user"
                history.append({"role": role, "content": clean_body})

        if not history or history[-1].get("content") != user_prompt:
            history.append({"role": "user", "content": user_prompt})

        try:
            if provider == "openrouter":
                return self._call_openrouter_api(api_key, model or "google/gemini-flash-1.5", system_prompt, history)
            elif provider == "gemini":
                return self._call_gemini_api(api_key, model or "gemini-1.5-flash", system_prompt, history)
            else:
                return self._call_openai_api(api_key, model or "gpt-4o-mini", system_prompt, history)
        except Exception as e:
            _logger.exception("Chatbot AI API call encountered an unexpected error: %s", str(e))
            return _(
                "<p>I'm sorry, I encountered an issue connecting to the AI service right now. "
                "Please try again in a moment or contact our admissions office.</p>"
            )

    def _call_openrouter_api(self, api_key, model, system_prompt, history):
        """Execute request to OpenRouter.ai API (OpenAI-compatible multi-model gateway)."""
        messages = [{"role": "system", "content": system_prompt}]
        for item in history:
            messages.append({"role": item["role"], "content": item["content"]})

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8070",
            "X-Title": "Harvard University Portal",
        }

        # Build candidate models to try in sequence (with LiquidAI support and free/paid fallbacks)
        models_to_try = [model]
        if "liquid" in model.lower() and not model.endswith(":free"):
            models_to_try.append(f"{model}:free")
        elif "liquid" in model.lower() and model.endswith(":free"):
            models_to_try.append(model.replace(":free", ""))
        models_to_try.append("openai/gpt-4o-mini")

        for m in models_to_try:
            payload = {
                "model": m,
                "messages": messages,
                "temperature": self.ai_temperature or 0.7,
                "max_tokens": 600,
            }

            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=25)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        msg_obj = choices[0].get("message", {})
                        reply_text = (msg_obj.get("content") or msg_obj.get("reasoning") or "").strip()
                        if reply_text:
                            return self._format_ai_response_html(reply_text)
                else:
                    _logger.warning("OpenRouter model '%s' returned status %d: %s", m, resp.status_code, resp.text[:120])
            except Exception as ex:
                _logger.warning("OpenRouter request for '%s' failed: %s", m, str(ex))

        return _("<p>I'm sorry, I encountered an issue connecting to the AI service. Please try again or contact our admissions office.</p>")

    def _call_openai_api(self, api_key, model, system_prompt, history):
        """Execute request to OpenAI Chat Completions API."""
        messages = [{"role": "system", "content": system_prompt}]
        for item in history:
            messages.append({"role": item["role"], "content": item["content"]})

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": self.ai_temperature or 0.7,
            "max_tokens": 500,
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            reply_text = data["choices"][0]["message"]["content"].strip()
            return self._format_ai_response_html(reply_text)
        else:
            err_msg = resp.text
            try:
                err_json = resp.json()
                err_msg = err_json.get("error", {}).get("message", resp.text)
            except Exception:
                pass
            _logger.error("OpenAI API error [%d]: %s", resp.status_code, err_msg)
            return _("<p><em>(OpenAI Service Notice: Error %d - %s)</em></p>") % (resp.status_code, err_msg)

    def _call_gemini_api(self, api_key, model, system_prompt, history):
        """Execute request to Google Gemini API."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {
            "Content-Type": "application/json",
        }

        contents = []
        for item in history:
            gemini_role = "model" if item["role"] == "assistant" else "user"
            contents.append({
                "role": gemini_role,
                "parts": [{"text": item["content"]}],
            })

        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}],
            },
            "contents": contents,
            "generationConfig": {
                "temperature": self.ai_temperature or 0.7,
                "maxOutputTokens": 500,
            },
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                reply_text = "".join(p.get("text", "") for p in parts).strip()
                return self._format_ai_response_html(reply_text)
            return _("<p>I received an empty response from Gemini. Please try again.</p>")
        else:
            err_msg = resp.text
            try:
                err_json = resp.json()
                err_msg = err_json.get("error", {}).get("message", resp.text)
            except Exception:
                pass
            _logger.error("Gemini API error [%d]: %s", resp.status_code, err_msg)
            return _("<p><em>(Gemini Service Notice: Error %d - %s)</em></p>") % (resp.status_code, err_msg)

    def _format_ai_response_html(self, text):
        """Format raw markdown or text into structured HTML suitable for chat bubbles."""
        if not text:
            return ""

        formatted = text
        # Convert **bold** to <strong>
        formatted = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", formatted)

        lines = formatted.split("\n")
        html_lines = []
        in_list = False

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                continue

            if stripped.startswith("- ") or stripped.startswith("* "):
                if not in_list:
                    html_lines.append("<ul class='ps-3 mb-2'>")
                    in_list = True
                html_lines.append(f"<li>{stripped[2:]}</li>")
            elif re.match(r"^\d+\.\s+", stripped):
                if not in_list:
                    html_lines.append("<ol class='ps-3 mb-2'>")
                    in_list = True
                content = re.sub(r"^\d+\.\s+", "", stripped)
                html_lines.append(f"<li>{content}</li>")
            else:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<p class='mb-1'>{stripped}</p>")

        if in_list:
            html_lines.append("</ul>")

        return "".join(html_lines)
