import json
import logging
from typing import Any, Self

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

SYNCED_FIELDS = {
    "company_id": "company_id",
    "owner_user_id": "user_id",
    "environment": "environment",
    "sequence": "sequence",
}


class IntegrationConnection(models.Model):
    _name = "integration.connection"
    _description = "Integration Connection"
    _order = "service_id, sequence, id"

    service_id = fields.Many2one(
        comodel_name="integration.service",
        string="Service",
        index=True,
        required=True,
        ondelete="cascade",
    )
    credential_id = fields.Many2one(
        comodel_name="credential.credential",
        string="Credential",
        index=True,
        ondelete="cascade",
        help="The secret this connection authenticates with. Empty only for a "
        "service that authenticates with nothing.",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        index=True,
        help="Empty: the connection serves every company that has none of its own.",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Personal To",
        index=True,
        help="Set for a personal connection, used only when the service allows them.",
    )
    environment = fields.Selection(
        selection=[
            ("test", "Test/Sandbox"),
            ("staging", "Staging"),
            ("production", "Production"),
        ],
        default="test",
        index=True,
        required=True,
        help="Which of the service's URLs this connection calls. Only connections in "
        "the service's own environment are used.",
    )
    service_environment = fields.Selection(
        related="service_id.environment",
        string="Service Environment",
        readonly=True,
    )
    base_url = fields.Char(
        string="Base URL",
        help="Overrides the service's URL for this connection, for a service whose "
        "address differs per installation: a device, a bridge, a portal.",
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    synced_from_credential = fields.Boolean(
        readonly=True,
        help="Kept in step with its credential's Outbound Endpoint, company, owner, "
        "environment and priority, for code that still binds credentials that way.",
    )

    @api.depends("service_id", "company_id", "environment", "user_id")
    def _compute_display_name(self):
        for connection in self:
            parts = [
                connection.service_id.name or "",
                connection.company_id.name or self.env._("All companies"),
                dict(self._fields["environment"].selection).get(
                    connection.environment, ""
                ),
            ]
            if connection.user_id:
                parts.append(connection.user_id.name)
            connection.display_name = " · ".join(part for part in parts if part)

    @api.constrains(
        "service_id", "company_id", "environment", "active", "user_id", "credential_id"
    )
    def _check_one_active_connection(self) -> None:
        constrained = self.filtered(
            lambda connection: (
                connection.active
                and not connection.service_id.allow_multiple_credentials
            )
        )
        if not constrained:
            return
        peers = self.search(
            [
                ("service_id", "in", constrained.service_id.ids),
                ("environment", "in", list(set(constrained.mapped("environment")))),
                ("active", "=", True),
            ]
        )
        ids_by_key: dict[tuple, set[int]] = {}
        for peer in peers:
            key = (
                peer.service_id.id,
                peer.company_id.id,
                peer.environment,
                peer.user_id.id,
            )
            ids_by_key.setdefault(key, set()).add(peer.id)
        for connection in constrained:
            key = (
                connection.service_id.id,
                connection.company_id.id,
                connection.environment,
                connection.user_id.id,
            )
            if ids_by_key.get(key, set()) - {connection.id}:
                raise ValidationError(
                    self.env._(
                        "Only one active connection per service, company and "
                        "environment, and per user for a personal one, unless the "
                        "service allows several."
                    )
                )

    @api.constrains("service_id", "credential_id")
    def _check_credential_serves_this_service(self) -> None:
        for connection in self:
            bound_to = connection.credential_id.endpoint_id
            if bound_to and bound_to != connection.service_id:
                raise ValidationError(
                    self.env._(
                        "Credential %(credential)s is bound to %(bound)s and cannot "
                        "connect %(service)s.",
                        credential=connection.credential_id.display_name,
                        bound=bound_to.display_name,
                        service=connection.service_id.display_name,
                    )
                )

    @api.model
    def _resolve(self, service, company=None, user=None, environment=None) -> Self:
        company_id = getattr(company, "id", company) or self.env.company.id
        environment = environment or service.environment
        base = [
            ("service_id", "=", service.id),
            ("environment", "=", environment),
            ("active", "=", True),
            "|",
            ("credential_id", "=", False),
            ("credential_id.active", "=", True),
        ]
        connections = self.sudo()
        scopes = []
        if service.allow_user_credentials:
            user_id = getattr(user, "id", user) or self.env.uid
            scopes += [
                [("user_id", "=", user_id), ("company_id", "=", company_id)],
                [("user_id", "=", user_id), ("company_id", "=", False)],
            ]
        scopes += [
            [("user_id", "=", False), ("company_id", "=", company_id)],
            [("user_id", "=", False), ("company_id", "=", False)],
        ]
        for scope in scopes:
            found = connections.search([*base, *scope], order="sequence, id", limit=1)
            if found:
                return found
        return connections.browse()

    @api.model
    def _for_credential(self, service, credential) -> Self:
        connections = self.sudo().search(
            [
                ("service_id", "=", service.id),
                ("credential_id", "=", credential.id),
                ("active", "=", True),
            ],
            order="sequence, id",
        )
        in_environment = connections.filtered(
            lambda connection: connection.environment == service.environment
        )
        if connections:
            return (in_environment or connections)[:1]
        if (
            self.sudo()
            .with_context(active_test=False)
            .search_count([("credential_id", "=", credential.id)], limit=1)
        ):
            return connections
        return self.sudo().new(
            {
                "service_id": service.id,
                "credential_id": credential.id,
                "environment": service.environment,
            }
        )

    def _base_url(self) -> str:
        self.check_singleton()
        if self.base_url:
            return self.base_url
        service = self.service_id
        if self.environment == "production":
            return service.endpoint_url
        return service.endpoint_url_test or service.endpoint_url

    def _get_auth_headers(self) -> dict[str, str]:
        self.check_singleton()
        credential = self.credential_id
        headers: dict[str, str] = {}
        if not credential:
            return headers
        auth_type = self.service_id.auth_type
        if auth_type == "bearer":
            token = credential._use_secret("integration:bearer", prefer="bearer_token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif auth_type == "api_key":
            api_key = credential._use_secret("integration:api_key", prefer="api_key")
            if api_key:
                headers.update(self.service_id._api_key_headers(api_key))
        elif auth_type == "oauth2":
            access_token = credential._use_secret_payload("integration:oauth").get(
                "oauth_access_token"
            )
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"
        if credential.custom_headers:
            try:
                headers.update(json.loads(credential.custom_headers))
            except json.JSONDecodeError, ValueError, TypeError:
                _logger.warning(
                    "Invalid custom_headers JSON for credential %s: %s",
                    credential.id,
                    credential.custom_headers[:100],
                )
        return headers

    @api.model
    def _sync_from_credentials(self, credentials) -> None:
        connections = self.sudo().with_context(active_test=False)
        synced_by_credential = connections.search(
            [
                ("credential_id", "in", credentials.ids),
                ("synced_from_credential", "=", True),
            ]
        ).grouped("credential_id")
        stale = connections.browse()
        to_create: list[dict[str, Any]] = []
        for credential in credentials:
            synced = synced_by_credential.get(credential, connections.browse())
            if not credential.endpoint_id:
                stale |= synced
                continue
            vals: dict[str, Any] = {
                "service_id": credential.endpoint_id.id,
                "credential_id": credential.id,
                "active": credential.active,
                "synced_from_credential": True,
                **{
                    target: (
                        credential[source].id
                        if isinstance(credential[source], models.BaseModel)
                        else credential[source]
                    )
                    for source, target in SYNCED_FIELDS.items()
                },
            }
            if synced:
                synced[:1].write(vals)
                stale |= synced[1:]
            else:
                to_create.append(vals)
        stale.unlink()
        if to_create:
            connections.create(to_create)
