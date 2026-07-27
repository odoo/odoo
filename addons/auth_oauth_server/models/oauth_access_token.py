from datetime import timedelta

from odoo import api, fields, models
from odoo.tools import SQL

from odoo.addons.auth_oauth_server_base.utils.oauth_utils import (
    _generate_hash, _generate_secret, _verify_hash, ACCESS_TOKEN_TTL_SECONDS, OAUTH_SECRET_INDEX_SIZE,
)


class OauthAccessToken(models.Model):
    _name = 'oauth.access.token'
    _description = 'OAuth Access Token'
    _auto = False

    oauth_token_id = fields.Many2one('oauth.token', required=True, ondelete='cascade')
    expiration_date = fields.Datetime(required=True)

    def init(self):
        table = SQL.identifier(self._table)
        self.env.cr.execute(SQL("""
        CREATE TABLE IF NOT EXISTS %(table)s (
            id serial primary key,
            access_token_hash varchar NOT NULL,
            access_token_index varchar(%(index_size)s) NOT NULL CHECK (char_length(access_token_index) = %(index_size)s),
            oauth_token_id integer NOT NULL REFERENCES oauth_token(id) ON DELETE CASCADE,
            expiration_date timestamp without time zone NOT NULL
        )
        """, table=table, index_size=OAUTH_SECRET_INDEX_SIZE))
        self.env.cr.execute(SQL(
            "CREATE INDEX IF NOT EXISTS %s ON %s (access_token_index)",
            SQL.identifier(self._table + "_access_token_index_index"),
            table,
        ))

    @api.model
    def _generate(self, oauth_token, access_token_ttl_seconds=ACCESS_TOKEN_TTL_SECONDS):
        access_token = _generate_secret()
        self.env.cr.execute(SQL(
            """
            INSERT INTO %(table)s
                (access_token_hash, access_token_index, oauth_token_id, expiration_date)
            VALUES
                (%(access_token_hash)s, %(access_token_index)s, %(oauth_token_id)s, %(expiration_date)s)
            """,
            table=SQL.identifier(self._table),
            access_token_hash=_generate_hash(access_token),
            access_token_index=access_token[:OAUTH_SECRET_INDEX_SIZE],
            oauth_token_id=oauth_token.id,
            expiration_date=fields.Datetime.now() + timedelta(seconds=access_token_ttl_seconds),
        ))
        return access_token

    @api.model
    def _retrieve_record(self, access_token):
        if not access_token:
            return self

        self.env.cr.execute(SQL(
            """
            SELECT id, access_token_hash
              FROM %(table)s
             WHERE access_token_index = %(index)s AND expiration_date > %(now)s
            """,
            table=SQL.identifier(self._table),
            index=access_token[:OAUTH_SECRET_INDEX_SIZE],
            now=fields.Datetime.now(),
        ))
        for row_id, access_token_hash in self.env.cr.fetchall():
            if _verify_hash(access_token, access_token_hash):
                return self.sudo().browse(row_id)
        return self

    @api.model
    def _check_credentials(self, scope, access_token):
        assert scope and access_token
        oauth_token = self._retrieve_record(access_token).oauth_token_id
        if oauth_token.scope != scope:
            return None
        if not oauth_token.client_id.active or not oauth_token.user_id.active:
            return None
        return oauth_token.user_id.id

    def _remove(self):
        # removing oauth_token record cascades back to this access token and to the refresh token.
        self.sudo().oauth_token_id.unlink()

    @api.autovacuum
    def _gc_expired_access_tokens(self):
        # The oauth.token record is kept: its refresh token outlives the access token and can still be
        # used to generate a new access token.
        self.sudo().search([('expiration_date', '<', fields.Datetime.now())]).unlink()
