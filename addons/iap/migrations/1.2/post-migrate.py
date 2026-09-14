from odoo import SUPERUSER_ID, api
from odoo.db import schema
from odoo.exceptions import UserError


def migrate(cr, version):
    if not version or not schema.column_exists(cr, "iap_account", "account_token"):
        return
    cr.execute(
        "SELECT id, account_token FROM iap_account "
        "WHERE COALESCE(account_token, '') != '' AND credential_id IS NULL ORDER BY id"
    )
    rows = cr.fetchall()
    if rows:
        _move_tokens(cr, rows)
    cr.execute("ALTER TABLE iap_account DROP COLUMN account_token")


def _move_tokens(cr, rows):
    env = api.Environment(cr, SUPERUSER_ID, {})
    if not env["credential.credential"]._is_encryption_key_configured():
        raise UserError(
            env._(
                "%(count)s IAP account token(s) move into encrypted credentials, which "
                "needs ODOO_API_ENCRYPTION_KEY. Set it and run the upgrade again.",
                count=len(rows),
            )
        )
    accounts = env["iap.account"].browse([account_id for account_id, _token in rows])
    for account, (_account_id, token) in zip(accounts, rows, strict=True):
        account.account_token = token
