from datetime import timedelta

from odoo import api, fields, models
from odoo.addons.auth_oauth_server_base.utils.oauth_utils import (
    _generate_hash, _generate_secret, _verify_hash, OAUTH_SECRET_INDEX_SIZE, REFRESH_TOKEN_TTL_SECONDS,
)
from odoo.tools import SQL


class OauthRefreshToken(models.Model):
    _name = 'oauth.refresh.token'
    _description = 'OAuth 2.1 Refresh Token'
    _auto = False

    expiration_date = fields.Datetime(required=True)
    oauth_token_id = fields.Many2one('oauth.token', required=True, ondelete='cascade')

    def init(self):
        table = SQL.identifier(self._table)
        self.env.cr.execute(SQL("""
        CREATE TABLE IF NOT EXISTS %(table)s (
            id serial primary key,
            refresh_token_hash varchar NOT NULL,
            refresh_token_index varchar(%(index_size)s) NOT NULL CHECK (char_length(refresh_token_index) = %(index_size)s),
            expiration_date timestamp without time zone NOT NULL,
            oauth_token_id integer NOT NULL REFERENCES oauth_token(id) ON DELETE CASCADE
        )
        """, table=table, index_size=OAUTH_SECRET_INDEX_SIZE))
        self.env.cr.execute(SQL(
            "CREATE INDEX IF NOT EXISTS %s ON %s (refresh_token_index)",
            SQL.identifier(self._table + "_refresh_token_index_index"),
            table,
        ))

    @api.model
    def _generate(self, oauth_token, refresh_token_ttl_seconds=REFRESH_TOKEN_TTL_SECONDS):
        refresh_token = _generate_secret()
        self.env.cr.execute(SQL(
            """
            INSERT INTO %(table)s
                (refresh_token_hash, refresh_token_index, expiration_date, oauth_token_id)
            VALUES
                (%(refresh_token_hash)s, %(refresh_token_index)s, %(expiration_date)s, %(oauth_token_id)s)
            """,
            table=SQL.identifier(self._table),
            refresh_token_hash=_generate_hash(refresh_token),
            refresh_token_index=refresh_token[:OAUTH_SECRET_INDEX_SIZE],
            expiration_date=fields.Datetime.now() + timedelta(seconds=refresh_token_ttl_seconds),
            oauth_token_id=oauth_token.id,
        ))
        return refresh_token

    @api.model
    def _retrieve_record(self, refresh_token):
        if not refresh_token:
            return self

        self.env.cr.execute(SQL(
            """
            SELECT id, refresh_token_hash
              FROM %(table)s
             WHERE refresh_token_index = %(index)s AND expiration_date > %(now)s
            """,
            table=SQL.identifier(self._table),
            index=refresh_token[:OAUTH_SECRET_INDEX_SIZE],
            now=fields.Datetime.now(),
        ))
        for row_id, refresh_token_hash in self.env.cr.fetchall():
            if _verify_hash(refresh_token, refresh_token_hash):
                return self.sudo().browse(row_id)
        return self

    @api.autovacuum
    def _gc_stale_refresh_tokens(self):
        # Removing oauth.token records will cascade to the linked res.users.apikeys and oauth.refresh.token records.
        stale_refresh_tokens = self.sudo().search([('expiration_date', '<', fields.Datetime.now())])
        stale_refresh_tokens.oauth_token_id.unlink()
