import uuid
from urllib.parse import urlsplit

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import SQL

from odoo.addons.auth_oauth_server_base.types.types import ClientRegistrationResult, ClientType
from odoo.addons.auth_oauth_server_base.utils.oauth_utils import _generate_secret, _generate_hash, _verify_hash

# Only IP literals count - "localhost" is excluded since its resolution can be hijacked (DNS rebinding, hosts file).
LOOPBACK_HOSTS = {'127.0.0.1', '::1'}


class OauthClient(models.Model):
    _name = 'oauth.client'
    _description = 'OAuth Client Application'
    _rec_name = 'client_name'
    _auto = False

    client_name = fields.Char(required=True)
    client_id = fields.Char(string="Client ID", required=True, copy=False, readonly=True)
    client_type = fields.Selection(
        [('public', 'Public'), ('confidential', 'Confidential')],
        required=True, readonly=True,
    )
    redirect_uris = fields.Text(
        required=True,
        help="One redirect URI per line. Must be HTTPS, except for http:// loopback URIs.",
    )
    resource_id = fields.Many2one(
        'oauth.resource', string="Resource", required=True, readonly=True, ondelete='cascade',
        help="The protected resource this client is registered under (e.g. rpc, mcp, etc)",
    )
    active = fields.Boolean(
        default=True,
        help="Archiving a client makes the authorization server block any new authorization or token request made with its client_id.",
    )

    def init(self):
        table = SQL.identifier(self._table)
        self.env.cr.execute(SQL("""
        CREATE TABLE IF NOT EXISTS %(table)s (
            id serial primary key,
            client_name varchar NOT NULL,
            client_id varchar NOT NULL,
            client_type varchar NOT NULL,
            client_secret_hash varchar,
            redirect_uris text NOT NULL,
            resource_id integer NOT NULL REFERENCES oauth_resource(id) ON DELETE CASCADE,
            active boolean NOT NULL DEFAULT true,
            CONSTRAINT oauth_client_client_id_unique UNIQUE (client_id),
            CONSTRAINT oauth_client_confidential_has_secret CHECK (client_type != 'confidential' OR client_secret_hash IS NOT NULL)
        )
        """, table=table))

    @api.constrains('redirect_uris')
    def _check_redirect_uris(self):
        for client in self:
            redirect_uris_list = [uri.strip() for uri in client.redirect_uris.splitlines() if uri.strip()]
            client._validate_redirect_uris(redirect_uris_list)

    def write(self, vals):
        immutable_fields = ["client_id", "client_type", "resource_id"]
        if any(field_name in vals for field_name in immutable_fields):
            raise UserError(self.env._("The %(field_names)s are generated once at registration and can never be changed.", field_names=", ".join(immutable_fields)))
        return super().write(vals)

    @api.model
    def _register_client(self, resource, client_name: str, redirect_uris: list[str], client_type: ClientType = 'public') -> ClientRegistrationResult:
        self._validate_redirect_uris(redirect_uris)
        client_id = uuid.uuid4().hex
        client_secret = _generate_secret() if client_type == 'confidential' else None
        self.env.cr.execute(SQL(
            """
            INSERT INTO %(table)s
                (client_id, client_name, client_type, client_secret_hash, redirect_uris, resource_id)
            VALUES
                (%(client_id)s, %(client_name)s, %(client_type)s, %(client_secret_hash)s, %(redirect_uris)s, %(resource_id)s)
            """,
            table=SQL.identifier(self._table),
            client_id=client_id,
            client_name=client_name,
            client_type=client_type,
            client_secret_hash=_generate_hash(client_secret) if client_secret else None,
            redirect_uris='\n'.join(redirect_uris),
            resource_id=resource.id,
        ))

        result: ClientRegistrationResult = {'client_id': client_id}
        if client_secret:
            result['client_secret'] = client_secret
        return result

    def _validate_redirect_uris(self, redirect_uris: list):
        if not redirect_uris:
            raise ValidationError(self.env._("At least one redirect_uri is required."))

        for uri in redirect_uris:
            uri_parts = urlsplit(uri)
            # RFC 6749 3.1.2: the redirection endpoint URI MUST NOT include a fragment component.
            if uri_parts.fragment:
                raise ValidationError(self.env._(
                    "Invalid redirect_uri %(uri)s: a redirect_uri must not include a fragment.",
                    uri=uri
                ))

            is_uri_valid = (
                (uri_parts.scheme == 'https' and uri_parts.hostname)
                or (uri_parts.scheme == 'http' and uri_parts.hostname in LOOPBACK_HOSTS)
            )

            if not is_uri_valid:
                raise ValidationError(self.env._(
                    "Invalid redirect_uri %(uri)s: only https:// URIs are allowed (or http:// for a loopback address).",
                    uri=uri
                ))

    def _verify_client_secret(self, client_secret: str | None) -> bool:
        self.ensure_one()
        if not client_secret:
            return False

        self.env.cr.execute(SQL(
            "SELECT client_secret_hash FROM %(table)s WHERE id = %(id)s",
            table=SQL.identifier(self._table), id=self.id,
        ))
        [client_secret_hash] = self.env.cr.fetchone()
        if not client_secret_hash:
            return False
        return _verify_hash(client_secret, client_secret_hash)

    def _is_redirect_uri_registered(self, redirect_uri: str) -> bool:
        """Whether `redirect_uri` matches one of this client's registered URIs.

        RFC 8252 §7.3: A native app (e.g. desktop, mobile or cli tool) can't host an HTTPS redirect
        endpoint and uses HTTP loopback redirect URIs instead. Also, a native app will bind to a new
        port on every run. So, the registered redirect URI won't include a port.
        """
        self.ensure_one()
        if not redirect_uri:
            return False

        redirect_uri_parts = urlsplit(redirect_uri)
        # RFC 6749 3.1.2: a redirect_uri must not include a fragment component.
        if redirect_uri_parts.fragment:
            return False

        registered_uris = [uri.strip() for uri in self.redirect_uris.splitlines() if uri.strip()]
        if redirect_uri in registered_uris:
            return True

        for candidate_match in registered_uris:
            candidate_match_parts = urlsplit(candidate_match)
            if (
                candidate_match_parts.scheme == 'http'
                and candidate_match_parts.hostname in LOOPBACK_HOSTS
                and redirect_uri_parts.scheme == candidate_match_parts.scheme
                and redirect_uri_parts.hostname == candidate_match_parts.hostname
                and redirect_uri_parts.path == candidate_match_parts.path
                and redirect_uri_parts.query == candidate_match_parts.query
            ):
                return True

        return False
