from datetime import timedelta

from odoo import api, fields, models
from odoo.addons.auth_oauth_server_base.utils.oauth_utils import (
    _generate_hash, _generate_secret, _verify_hash, OAUTH_SECRET_INDEX_SIZE,
)
from odoo.tools import SQL


class OauthAuthorizationCode(models.Model):
    _name = 'oauth.authorization.code'
    _description = 'OAuth 2.1 Authorization Code'
    _auto = False

    client_id = fields.Many2one('oauth.client', required=True, ondelete='cascade')
    redirect_uri = fields.Char(required=True)
    code_challenge = fields.Char(required=True)
    code_challenge_method = fields.Selection([('S256', 'S256')], required=True, default='S256')
    scope = fields.Char(required=True)
    user_id = fields.Many2one('res.users', required=True, ondelete='cascade')
    expiration_date = fields.Datetime(required=True)

    def init(self):
        table = SQL.identifier(self._table)
        self.env.cr.execute(SQL("""
        CREATE TABLE IF NOT EXISTS %(table)s (
            id serial primary key,
            code_hash varchar NOT NULL,
            code_index varchar(%(index_size)s) NOT NULL CHECK (char_length(code_index) = %(index_size)s),
            client_id integer NOT NULL REFERENCES oauth_client(id) ON DELETE CASCADE,
            redirect_uri varchar NOT NULL,
            code_challenge varchar NOT NULL,
            code_challenge_method varchar NOT NULL,
            scope varchar NOT NULL,
            user_id integer NOT NULL REFERENCES res_users(id) ON DELETE CASCADE,
            expiration_date timestamp without time zone NOT NULL
        )
        """, table=table, index_size=OAUTH_SECRET_INDEX_SIZE))
        self.env.cr.execute(SQL(
            "CREATE INDEX IF NOT EXISTS %s ON %s (code_index)",
            SQL.identifier(self._table + "_code_index_index"),
            table,
        ))

    def _generate(self, client, redirect_uri, code_challenge, scope, user, code_ttl_seconds=120):
        code = _generate_secret()
        self.env.cr.execute(SQL(
            """
            INSERT INTO %(table)s
                (code_hash, code_index, client_id, redirect_uri, code_challenge, code_challenge_method, scope, user_id, expiration_date)
            VALUES
                (%(code_hash)s, %(code_index)s, %(client_id)s, %(redirect_uri)s, %(code_challenge)s, %(code_challenge_method)s, %(scope)s, %(user_id)s, %(expiration_date)s)
            """,
            table=SQL.identifier(self._table),
            code_hash=_generate_hash(code),
            code_index=code[:OAUTH_SECRET_INDEX_SIZE],
            client_id=client.id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method='S256',
            scope=scope,
            user_id=user.id,
            expiration_date=fields.Datetime.now() + timedelta(seconds=code_ttl_seconds),
        ))
        return code

    @api.model
    def _retrieve_record(self, code, client, redirect_uri):
        self.env.cr.execute(SQL(
            """
            SELECT id, code_hash
              FROM %(table)s
             WHERE code_index = %(code_index)s
                   AND client_id = %(client_id)s
                   AND redirect_uri = %(redirect_uri)s
                   AND expiration_date > %(now)s
            """,
            table=SQL.identifier(self._table),
            code_index=code[:OAUTH_SECRET_INDEX_SIZE],
            client_id=client.id,
            redirect_uri=redirect_uri,
            now=fields.Datetime.now(),
        ))
        matching_id = next(
            (row_id for row_id, code_hash in self.env.cr.fetchall() if _verify_hash(code, code_hash)),
            None,
        )
        return self.sudo().browse(matching_id)

    @api.autovacuum
    def _gc_expired_codes(self):
        self.sudo().search([('expiration_date', '<', fields.Datetime.now())]).unlink()
