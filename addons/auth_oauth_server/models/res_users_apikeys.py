from odoo import fields, models
from odoo.tools import SQL

from odoo.addons.base.models.res_users import INDEX_SIZE, KEY_CRYPT_CONTEXT


class ResUsersApikeys(models.Model):
    _inherit = 'res.users.apikeys'

    oauth_token_id = fields.Many2one('oauth.token', ondelete='cascade')

    def init(self):
        # res.users.apikeys is _auto=False, so the column of the new field has to be added by hand.
        super().init()
        # Other models like auth_totp.device inherit from the res.users.apikeys model, but should not have the oauth_token_id column.
        if self._name != 'res.users.apikeys':
            return

        self.env.cr.execute(SQL("""
        ALTER TABLE %(table)s
            ADD COLUMN IF NOT EXISTS oauth_token_id integer REFERENCES oauth_token(id) ON DELETE CASCADE
        """, table=SQL.identifier(self._table)))

    def _remove(self):
        oauth_tokens = self.sudo().oauth_token_id
        result = super()._remove()
        oauth_tokens.unlink()
        return result

    def _generate_access_token(self, scope, name, expiration_date):
        access_token = self._generate(scope, name, expiration_date)
        access_token_id = self._retrieve_record(access_token)[0]
        return access_token, access_token_id

    def _retrieve_record(self, key):
        if not key:
            return None, None

        self.env.cr.execute(SQL(
            """
            SELECT id, user_id, key
              FROM %(table)s
             WHERE index = %(index)s AND (expiration_date IS NULL OR expiration_date > %(now)s)
            """,
            table=SQL.identifier(self._table),
            index=key[:INDEX_SIZE],
            now=fields.Datetime.now(),
        ))
        for row_id, user_id, key_hash in self.env.cr.fetchall():
            if KEY_CRYPT_CONTEXT.verify(key, key_hash):
                return row_id, user_id
        return None, None
