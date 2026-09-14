import logging

from odoo import SUPERUSER_ID
from odoo.api import Environment

_logger = logging.getLogger(__name__)


def _column_exists(cr, table: str, column: str) -> bool:
    cr.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s AND column_name = %s
        """,
        [table, column],
    )
    return cr.fetchone() is not None


def migrate(cr, version):
    if not version:
        return

    if not _column_exists(cr, "integration_service", "oauth_client_secret_encrypted"):
        _logger.info("No legacy oauth_client_secret_encrypted column; nothing to do.")
        return

    env = Environment(cr, SUPERUSER_ID, {})
    credential_model = env["credential.credential"]
    oauth2_category = env.ref(
        "credential.credential_category_oauth2",
        raise_if_not_found=False,
    )

    cr.execute(
        """
        SELECT id, company_id, environment, oauth_client_id,
               oauth_client_secret_encrypted
        FROM integration_service
        WHERE oauth_client_secret_encrypted IS NOT NULL
        """
    )
    rows = cr.fetchall()
    migrated = errors = 0
    for row_id, company_id, environment, client_id, encrypted in rows:
        endpoint = env["integration.service"].browse(row_id)
        plaintext = credential_model._decrypt_value_safe(bytes(encrypted), default=None)
        if not plaintext:
            errors += 1
            _logger.warning(
                "Endpoint %s (%s): could not decrypt legacy OAuth client "
                "secret; skipping (configure it manually on the credential).",
                row_id,
                endpoint.code,
            )
            continue
        existing = credential_model.search(
            [("endpoint_id", "=", row_id), ("category_id", "=", oauth2_category.id)],
            limit=1,
        )
        values = {
            "oauth_client_secret": plaintext,
            "oauth_client_id": client_id or False,
        }
        if existing:
            existing.write(values)
        else:
            credential_model.create(
                {
                    "name": f"{endpoint.display_name} OAuth Client (Migrated)",
                    "category_id": oauth2_category.id,
                    "endpoint_id": row_id,
                    "company_id": company_id or env.company.id,
                    "environment": environment or "test",
                    **values,
                }
            )
        migrated += 1

    _logger.info(
        "OAuth client secret vault migration: %s migrated, %s skipped.",
        migrated,
        errors,
    )

    cr.execute(
        "ALTER TABLE integration_service "
        "DROP COLUMN IF EXISTS oauth_client_secret_encrypted, "
        "DROP COLUMN IF EXISTS encryption_key_version"
    )
