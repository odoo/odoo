from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MixinIntegrationChannel(models.AbstractModel):
    _name = "mixin.integration.channel"
    _inherit = ["mixin.credential.auth"]
    _description = "Communication Channel Mixin"

    name = fields.Char(
        translate=True,
        required=True,
        help="Human-readable name for this channel",
    )
    active = fields.Boolean(
        default=True,
        index=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        help="Company that owns this channel (for multi-tenancy isolation)",
    )
    sequence = fields.Integer(default=10)
    code = fields.Char(
        index=True,
        help="Unique identifier code for programmatic access",
    )
    description = fields.Text(
        translate=True,
        help="Description of what this channel does",
    )

    retry_enabled = fields.Boolean(
        string="Enable Retry",
        default=True,
        help="Automatically retry failed operations with exponential backoff",
    )
    retry_max_attempts = fields.Integer(
        string="Max Retry Attempts",
        default=3,
        help="Maximum number of retry attempts before marking as failed",
    )
    retry_initial_delay = fields.Integer(
        string="Initial Retry Delay (seconds)",
        default=60,
        help="Initial delay before first retry. Increases exponentially.",
    )
    retry_backoff_type = fields.Selection(
        selection=[
            ("fixed", "Fixed Delay"),
            ("linear", "Linear Backoff"),
            ("exponential", "Exponential Backoff"),
        ],
        default="exponential",
        help="Strategy for increasing delay between retries",
    )

    date_last_activity = fields.Datetime(
        string="Last Activity",
        readonly=True,
        help="Timestamp of most recent activity (request received or sent)",
    )

    @api.constrains("rate_limit_requests", "rate_limit_enabled")
    def _check_rate_limit_requests(self):
        for record in self:
            if record.rate_limit_enabled and record.rate_limit_requests <= 0:
                raise ValidationError(
                    self.env._("Rate limit requests must be greater than 0"),
                )

    @api.constrains("retry_max_attempts", "retry_enabled")
    def _check_retry_max_attempts(self):
        for record in self:
            if record.retry_enabled and record.retry_max_attempts <= 0:
                raise ValidationError(
                    self.env._("Max retry attempts must be greater than 0"),
                )

    @api.constrains("retry_initial_delay", "retry_enabled")
    def _check_retry_initial_delay(self):
        for record in self:
            if record.retry_enabled and record.retry_initial_delay <= 0:
                raise ValidationError(
                    self.env._("Initial retry delay must be greater than 0"),
                )

    def get_retry_delay(self, attempt_number):
        self.check_singleton()

        base_delay = self.retry_initial_delay

        if self.retry_backoff_type == "fixed":
            return base_delay
        if self.retry_backoff_type == "linear":
            return base_delay * attempt_number
        return base_delay * (2 ** (attempt_number - 1))

    def is_retry_required(self, attempt_number):
        self.check_singleton()

        if not self.retry_enabled:
            return False

        return attempt_number < self.retry_max_attempts

    def update_date_last_activity(self):
        self.write({"date_last_activity": fields.Datetime.now()})

    _api_event_direction = None

    event_log_ids = fields.One2many(
        comodel_name="integration.exchange",
        compute="_compute_event_log_ids",
    )

    def _integration_exchange_domain(self):
        if not self._api_event_direction:
            raise NotImplementedError(
                f"{self._name} inherits mixin.integration.channel without declaring "
                "_api_event_direction, so its event log cannot be scoped",
            )
        return [
            ("channel_id", "in", [f"{record._name},{record.id}" for record in self]),
            ("direction", "=", self._api_event_direction),
        ]

    def _compute_event_log_ids(self):
        logs_by_ref: dict[str, list[int]] = {}
        if self.ids:
            groups = self.env["integration.exchange"]._read_group(
                domain=self._integration_exchange_domain(),
                groupby=["channel_id"],
                aggregates=["id:recordset"],
            )
            for ref, recordset in groups:
                logs_by_ref[ref] = recordset.ids
        for record in self:
            ref = f"{record._name},{record.id}"
            record.event_log_ids = [(6, 0, logs_by_ref.get(ref, []))]
