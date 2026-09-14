import logging

from odoo.db import schema
from odoo.exceptions import ValidationError
from odoo.tools import SQL

_logger = logging.getLogger(__name__)

PROVIDER_BY_CATALOG_CODE = {
    "groq": "gateway_ml.ai_provider_groq",
    "gemini": "gateway_ml.ai_provider_google",
    "openai": "gateway_ml.ai_provider_openai",
    "deepseek": "gateway_ml.ai_provider_deepseek",
    "moonshot": "gateway_ml.ai_provider_moonshot",
    "claude": "gateway_ml.ai_provider_anthropic",
}


def provider_for_catalog_code(env, code):
    xmlid = PROVIDER_BY_CATALOG_CODE.get(code or "")
    return env.ref(xmlid, raise_if_not_found=False) if xmlid else None


def chat_model_for_code(provider, code):
    code = (code or "").strip()
    if not provider or not code:
        return provider.env["gateway.ml.model"] if provider else None
    models = provider.env["gateway.ml.model"].sudo().with_context(active_test=False)
    model = models.search([("provider_id", "=", provider.id), ("code", "=", code)])
    if model:
        return model[:1]
    _logger.info(
        "gateway_ml: %s had no row for model %s, which an assistant named; added",
        provider.name,
        code,
    )
    chat_default = provider._service_for("chat").model_id
    return models.create(
        {
            "provider_id": provider.id,
            "name": code,
            "code": code,
            "kind": "chat",
            "has_vision": chat_default.has_vision,
        }
    )


def connect_credential(env, provider, credential, label):
    if not provider or not credential or not credential.active:
        return
    company = credential.company_id or env.company
    connections = env["integration.connection"].sudo()
    for service in provider.service_ids.filtered(
        lambda row: row.operation in ("chat", "transcribe")
    ).service_id:
        if service.auth_type == "none":
            continue
        existing = connections._resolve(service, company=company)
        if existing and not existing.credential_id:
            if not credential.endpoint_id or credential.endpoint_id == service:
                existing.credential_id = credential
            continue
        if existing:
            if existing.credential_id != credential:
                _logger.warning(
                    "gateway_ml: %s keeps using %s's connection to %s; the key it "
                    "held of its own (%s) is no longer used",
                    label,
                    company.name,
                    service.code,
                    credential.display_name,
                )
            continue
        bound = credential.endpoint_id
        if bound and bound != service:
            _logger.warning(
                "gateway_ml: %s's key is bound to %s and cannot connect %s; give "
                "%s a connection to %s",
                label,
                bound.code,
                service.code,
                company.name,
                service.code,
            )
            continue
        try:
            with env.cr.savepoint():
                connections.create(
                    {
                        "name": label,
                        "service_id": service.id,
                        "credential_id": credential.id,
                        "company_id": company.id,
                        "environment": service.environment,
                    }
                )
        except ValidationError as error:
            _logger.warning(
                "gateway_ml: %s could not connect %s to %s: %s",
                label,
                company.name,
                service.code,
                error,
            )


def adopt_assistant_columns(env, model_name, prefix):
    model = env[model_name]
    table = model._table
    provider_column = f"{prefix}_ai_provider"
    model_column = f"{prefix}_ai_model"
    credential_column = f"{prefix}_ai_credential_id"
    if not all(
        schema.column_exists(env.cr, table, column)
        for column in (provider_column, model_column, credential_column)
    ):
        return
    env.cr.execute(
        SQL(
            "SELECT id, %s, %s, %s FROM %s ORDER BY id",
            SQL.identifier(provider_column),
            SQL.identifier(model_column),
            SQL.identifier(credential_column),
            SQL.identifier(table),
        )
    )
    rows = env.cr.fetchall()
    credentials = env["credential.credential"].sudo().with_context(active_test=False)
    for record_id, code, model_code, credential_id in rows:
        record = model.browse(record_id)
        provider = provider_for_catalog_code(env, code)
        if not provider:
            _logger.warning(
                "gateway_ml: %s %s named the unknown assistant vendor %r; it keeps "
                "its default provider",
                model_name,
                record_id,
                code,
            )
            continue
        record.write(
            {
                f"{prefix}_ai_provider_id": provider.id,
                f"{prefix}_ai_model_id": chat_model_for_code(provider, model_code).id,
            }
        )
        if credential_id:
            connect_credential(
                env,
                provider,
                credentials.browse(credential_id).exists(),
                f"{record.display_name} ({provider.name})",
            )
