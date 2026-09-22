from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DeviceConfig(models.Model):
    _name = "device.profile"
    _description = "Remote Device Configuration"
    _order = "name"

    name = fields.Char(
        required=True,
        help="Name for this configuration profile",
    )
    active = fields.Boolean(
        default=True,
        index=True,
        help="Whether this configuration is active",
    )
    description = fields.Text(help="Description of this configuration profile")

    manufacturer = fields.Char(help="Device manufacturer (e.g., Teltonika, Queclink)")
    model = fields.Char(help="Device model number")

    protocol = fields.Selection(
        selection=[
            ("http", "HTTP/REST"),
            ("https", "HTTPS/REST"),
        ],
        default="http",
        help="Primary communication protocol for devices using this config. "
        "A protocol module adds its own value here alongside the one it adds "
        "to device.device.comm_protocol.",
    )
    service_id = fields.Many2one(
        comodel_name="integration.service",
        string="Service",
        copy=False,
        readonly=True,
        ondelete="restrict",
        help="How Odoo dials the devices of this model: the default address, "
        "the authentication scheme, the timeouts. One per profile; every "
        "device's own connection hangs from it.",
    )
    endpoint_url = fields.Char(
        related="service_id.endpoint_url",
        string="Default Address",
        readonly=False,
        help="The base URL a device of this model answers on when it names no "
        "address of its own (the AWS IoT ATS endpoint, a shared gateway).",
    )
    http_timeout = fields.Integer(
        related="service_id.timeout_read",
        readonly=False,
        help="Seconds Odoo waits for a device of this model to answer.",
    )
    http_method = fields.Selection(
        selection=[
            ("GET", "GET"),
            ("POST", "POST"),
            ("PUT", "PUT"),
        ],
        default="GET",
        help="HTTP method for data requests",
    )

    http_headers = fields.Text(
        help="Default custom HTTP headers in JSON format. Can be overridden at device level."
    )

    auto_reconnect = fields.Boolean(
        default=True,
        help="Automatically reconnect if connection is lost (applies to all protocols)",
    )

    auth_type = fields.Selection(
        related="service_id.auth_type",
        readonly=False,
        help="Authentication scheme the devices of this model are dialled with.",
    )
    credential_id = fields.Many2one(
        comodel_name="credential.credential",
        string="Shared Dial Secret",
        copy=False,
        ondelete="set null",
        groups="base.group_system",
        help="The secret every device of this model is dialled with unless it "
        "carries its own: a login and password, a bearer token, an API key.",
    )
    auth_username = fields.Char(
        compute="_compute_auth_secrets",
        inverse="_inverse_auth_username",
        groups="base.group_system",
        help="Login of the shared dial secret, for a scheme that takes one.",
    )
    auth_password = fields.Char(
        compute="_compute_auth_secrets",
        inverse="_inverse_auth_password",
        groups="base.group_system",
        help="Password for Basic Auth (system admins only)",
    )
    auth_token = fields.Char(
        compute="_compute_auth_secrets",
        inverse="_inverse_auth_token",
        groups="base.group_system",
        help="API token or key for token-based authentication",
    )
    ca_certificate_id = fields.Many2one(
        comodel_name="certificate.certificate",
        string="Server Authority",
        help="The authority the devices' servers are checked against when it "
        "is not one of the system's (a private broker CA, Amazon Root CA 1).",
    )

    @api.depends("credential_id")
    def _compute_auth_secrets(self):
        for config in self:
            credential = config.sudo().credential_id
            payload = (
                credential._use_secret_payload("device:dial") if credential else {}
            )
            config.auth_username = payload.get("username") or False
            config.auth_password = payload.get("password") or False
            config.auth_token = payload.get("bearer_token") or False

    def _inverse_auth_username(self):
        self._store_auth_secret("username", "auth_username")

    def _inverse_auth_password(self):
        self._store_auth_secret("password", "auth_password")

    def _inverse_auth_token(self):
        self._store_auth_secret("bearer_token", "auth_token")

    @api.model_create_multi
    def create(self, vals_list):
        profiles = super().create(vals_list)
        for profile, vals in zip(profiles, vals_list, strict=True):
            profile._ensure_service(vals)
        return profiles

    def write(self, vals):
        result = super().write(vals)
        if "name" in vals:
            self.sudo().service_id.write({"name": self._service_name()})
        if "credential_id" in vals:
            self.sudo().credential_id.filtered(
                lambda credential: not credential.endpoint_id
            ).write({"endpoint_id": self.service_id.id})
        if vals.keys() & self._stream_fields():
            self.device_ids._sync_stream()
        if vals.keys() & self._connection_fields():
            self.device_ids._sync_connection()
        return result

    def unlink(self):
        services = self.sudo().service_id
        result = super().unlink()
        services.unlink()
        return result

    def _service_name(self):
        self.check_singleton()
        return f"Device profile: {self.name}"

    def _ensure_service(self, vals=None):
        self.check_singleton()
        if self.service_id:
            return self.service_id
        vals = vals or {}
        service = (
            self.env["integration.service"]
            .sudo()
            .create(
                {
                    "name": self._service_name(),
                    "code": f"device_profile_{self.id}",
                    "category": "device",
                    "per_record_connections": True,
                    "auth_type": vals.get("auth_type") or "none",
                    "endpoint_url": vals.get("endpoint_url") or False,
                    "timeout_read": vals.get("http_timeout") or 30,
                    "rate_limit_enabled": False,
                    "health_check_enabled": False,
                }
            )
        )
        self.sudo().service_id = service
        if self.sudo().credential_id and not self.sudo().credential_id.endpoint_id:
            self.sudo().credential_id.endpoint_id = service
        return service

    @api.model
    def _stream_fields(self):
        return frozenset(
            {
                "endpoint_url",
                "http_timeout",
                "auth_type",
                "auth_username",
                "credential_id",
                "ca_certificate_id",
            }
        )

    @api.model
    def _connection_fields(self):
        return frozenset({"credential_id", "service_id"})

    def _store_auth_secret(self, key, field_name):
        category = self.env.ref("credential.credential_category_custom")
        for config in self:
            value = config[field_name] or False
            credential = config.sudo().credential_id
            if credential:
                credential.write({key: value})
            elif value:
                config.sudo().credential_id = (
                    self.env["credential.credential"]
                    .sudo()
                    .create(
                        {
                            "name": f"Device profile {config.name} [#{config.id}]",
                            "category_id": category.id,
                            "company_id": False,
                            "endpoint_id": config.sudo().service_id.id,
                            key: value,
                        }
                    )
                )

    odometer_correction_factor = fields.Float(
        default=1.0,
        help="Factor to correct odometer readings (e.g., 0.001 to convert from meters to kilometers)",
    )

    alert_on_disconnect = fields.Boolean(
        default=True,
        help="Alert when device stops reporting data",
    )
    disconnect_timeout = fields.Integer(
        default=0,
        help="Seconds without inbound data before devices on this profile are "
        "considered stale. 0 = inherit the global "
        "'device.disconnect_timeout_default' parameter. Overridden by the "
        "device category when that sets its own.",
    )

    data_retention_days = fields.Integer(
        default=90,
        help="How long to keep historical data from devices using this profile. "
        "Leave at 0 to fall back to the global retention setting.",
    )

    device_ids = fields.One2many(
        comodel_name="device.device",
        inverse_name="config_id",
        help="Devices using this configuration",
    )
    device_count = fields.Count(
        count_of="device_ids",
        help="Number of devices using this configuration",
    )

    @api.constrains("odometer_correction_factor")
    def _check_odometer_correction_factor(self):
        for config in self:
            if config.odometer_correction_factor <= 0:
                raise ValidationError(
                    self.env._("Odometer correction factor must be positive")
                )

    def action_view_devices(self):
        self.check_singleton()
        return {
            "name": f"Devices - {self.name}",
            "type": "ir.actions.act_window",
            "res_model": "device.device",
            "view_mode": "list,form",
            "domain": [("config_id", "=", self.id)],
            "context": {
                "default_config_id": self.id,
            },
        }

    def get_corrected_odometer(self, raw_odometer):
        self.check_singleton()
        return raw_odometer * self.odometer_correction_factor
