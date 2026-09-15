import logging

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools import str2bool

from odoo.addons.base.models.ir_module import assert_log_admin_access

_logger = logging.getLogger(__name__)


class CalendarProviderConfig(models.TransientModel):
    _name = "calendar.provider.config"
    _description = "Calendar Provider Configuration Wizard"

    external_calendar_provider = fields.Selection(
        selection=[("google", "Google"), ("microsoft", "Outlook")],
        string="Choose an external calendar to configure",
        default="google",
    )

    # Allow to sync with eventually existing ICP keys without creating them if respective module is not installed
    # Using same field names and strings as their respective res.config.settings
    cal_client_id = fields.Char(
        string="Google Client_id",
        default=lambda self: self.env["ir.config_parameter"].get_param(
            "google_calendar_client_id"
        ),
    )
    cal_client_secret = fields.Char(
        string="Google Client_key",
        default=lambda self: self.env["credential.credential"]._get_system_secret(
            "google_calendar_client_secret"
        ),
    )
    cal_sync_paused = fields.Boolean(
        string="Google Synchronization Paused",
        default=lambda self: str2bool(
            self.env["ir.config_parameter"].get_param("google_calendar_sync_paused"),
            default=False,
        ),
    )
    microsoft_outlook_client_identifier = fields.Char(
        string="Outlook Client Id",
        default=lambda self: self.env["ir.config_parameter"].get_param(
            "microsoft_calendar_client_id"
        ),
    )
    microsoft_outlook_client_secret = fields.Char(
        string="Outlook Client Secret",
        default=lambda self: self.env["credential.credential"]._get_system_secret(
            "microsoft_calendar_client_secret"
        ),
    )
    microsoft_outlook_sync_paused = fields.Boolean(
        string="Outlook Synchronization Paused",
        default=lambda self: str2bool(
            self.env["ir.config_parameter"].get_param("microsoft_calendar_sync_paused"),
            default=False,
        ),
    )

    @assert_log_admin_access
    def action_calendar_prepare_external_provider_sync(self):
        """Called by the wizard to configure an external calendar provider without requiring users
        to access the general settings page.
        Make sure that the provider calendar module is installed or install it. Then, set
        the API keys into the applicable config parameters.
        """
        self.check_singleton()
        # `assert_log_admin_access`'s own audit line names this wizard's
        # generic display_name, not the provider it's actually configuring --
        # log that explicitly.
        _logger.info(
            "Configuring the %s calendar provider for user %s #%s",
            self.external_calendar_provider,
            self.env.user.login,
            self.env.user.id,
        )
        calendar_module = self.env["ir.module.module"].search(
            [("name", "=", f"{self.external_calendar_provider}_calendar")]
        )
        if not calendar_module:
            raise UserError(
                _(
                    "No module found to configure the %(provider)s calendar.",
                    provider=self.external_calendar_provider,
                )
            )

        if calendar_module.state != "installed":
            calendar_module.button_immediate_install()

        if self.external_calendar_provider == "google":
            self.env["ir.config_parameter"].set_param(
                "google_calendar_client_id", self.cal_client_id
            )
            self.env["credential.credential"]._set_system_secret(
                "google_calendar_client_secret", self.cal_client_secret
            )
            self.env["ir.config_parameter"].set_param(
                "google_calendar_sync_paused", self.cal_sync_paused
            )
        elif self.external_calendar_provider == "microsoft":
            self.env["ir.config_parameter"].set_param(
                "microsoft_calendar_client_id", self.microsoft_outlook_client_identifier
            )
            self.env["credential.credential"]._set_system_secret(
                "microsoft_calendar_client_secret", self.microsoft_outlook_client_secret
            )
            self.env["ir.config_parameter"].set_param(
                "microsoft_calendar_sync_paused", self.microsoft_outlook_sync_paused
            )
