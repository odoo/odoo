import logging
import os

_logger = logging.getLogger(__name__)


def _param(env, key: str, default: str | None = None) -> str | None:
    return env["ir.config_parameter"].sudo().get_param(key, default)


def _env_or_param(env, env_key: str, param_key: str, default: str | None = None) -> str | None:
    v = os.getenv(env_key)
    if v is not None and v.strip() != "":
        return v.strip()
    return _param(env, param_key, default)


def _safe_values(model, values: dict) -> dict:
    existing = set(model._fields.keys())
    return {k: v for k, v in values.items() if k in existing}


def configure_amazon_ses_outgoing_mail(env) -> None:
    enabled = (_param(env, "via.ses.enabled", "false") or "").lower() == "true"
    if not enabled:
        return

    mail_server_model = env["ir.mail_server"].sudo()

    name = _env_or_param(env, "VIA_SES_SERVER_NAME", "via.ses.server_name", "Amazon SES (ViaSuite)")
    host = _env_or_param(env, "VIA_SES_SMTP_HOST", "via.ses.smtp_host")
    port_raw = _env_or_param(env, "VIA_SES_SMTP_PORT", "via.ses.smtp_port", "587")
    encryption = _env_or_param(env, "VIA_SES_SMTP_ENCRYPTION", "via.ses.smtp_encryption", "starttls")
    from_filter = _env_or_param(env, "VIA_SES_FROM_FILTER", "via.ses.from_filter", "@viafronteira.com")

    user = (os.getenv("VIA_SES_SMTP_USER") or "").strip()
    password = (os.getenv("VIA_SES_SMTP_PASS") or "").strip()

    try:
        port = int(port_raw or "587")
    except ValueError:
        port = 587

    record = mail_server_model.search([("name", "=", name)], limit=1)

    values = _safe_values(mail_server_model, {
        "name": name,
        "smtp_host": host,
        "smtp_port": port,
        "smtp_encryption": encryption,
        "from_filter": from_filter,
        "active": True,
        "sequence": 10,
        **({"smtp_user": user, "smtp_pass": password} if user and password else {}),
    })

    if not user or not password:
        _logger.warning("SES bootstrap: missing VIA_SES_SMTP_USER/VIA_SES_SMTP_PASS (server will exist but won't authenticate).")

    if record:
        record.write(values)
    else:
        mail_server_model.create(values)

    _logger.info("SES bootstrap configured: %s (%s:%s %s)", name, host, port, encryption)