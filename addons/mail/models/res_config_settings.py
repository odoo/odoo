import datetime
import typing

from odoo import _, fields, models
from odoo.exceptions import UserError

if typing.TYPE_CHECKING:
    from .mail_alias_domain import MailAliasDomain


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    external_email_server_default = fields.Boolean(
        string="Use Custom Email Servers",
        config_parameter="base_setup.default_external_email_server",
    )
    fail_counter = fields.Integer(
        string="Fail Mail",
        compute="_compute_fail_counter",
    )
    alias_domain_id: MailAliasDomain = fields.Many2one(
        comodel_name="mail.alias.domain",
        related="company_id.alias_domain_id",
        string="Alias Domain",
        readonly=False,
        help="If you have setup a catch-all email domain redirected to the Odoo server, enter the domain name here.",
    )
    module_google_gmail = fields.Boolean(string="Support Gmail Authentication")
    module_microsoft_outlook = fields.Boolean(string="Support Outlook Authentication")
    restrict_template_rendering = fields.Boolean(
        config_parameter="mail.restrict.template.rendering",
        help="Users will still be able to render templates.\n"
        "However only Mail Template Editors will be able to create new dynamic templates or modify existing ones.",
    )
    use_twilio_rtc_servers = fields.Boolean(
        string="Use Twilio ICE servers",
        config_parameter="mail.use_twilio_rtc_servers",
        help="If you want to use twilio as TURN/STUN server provider",
    )
    twilio_account_sid = fields.Char(
        string="Account SID",
        config_parameter="mail.twilio_account_sid",
    )
    twilio_account_token = fields.Char(
        string="Account Auth Token",
        secret_parameter="mail.twilio_account_token",
    )
    use_sfu_server = fields.Boolean(
        string="Use SFU server",
        config_parameter="mail.use_sfu_server",
        help="If you want to setup SFU server for large group calls.",
    )
    sfu_server_url = fields.Char(
        string="SFU Server URL",
        config_parameter="mail.sfu_server_url",
    )
    sfu_server_key = fields.Char(
        string="SFU Server key",
        secret_parameter="mail.sfu_server_key",
        help="Base64 encoded key",
    )
    email_primary_color = fields.Char(
        related="company_id.email_primary_color",
        readonly=False,
    )
    email_secondary_color = fields.Char(
        related="company_id.email_secondary_color",
        readonly=False,
    )

    tenor_api_key = fields.Char(
        string="Klipy API key",
        secret_parameter="discuss.klipy_api_key",
        help="Add a Klipy GIF API key to enable GIFs support. https://docs.klipy.com/getting-started\n"
        "If you were using a Tenor GIF API key (service shutdown on June 30, 2026), please replace it here with a Klipy GIF API key",
    )
    google_translate_api_key = fields.Char(
        string="Message Translation API Key",
        secret_parameter="mail.google_translate_api_key",
        help="A valid Google API key is required to enable message translation. https://cloud.google.com/translate/docs/setup",
    )

    def _compute_fail_counter(self) -> None:
        previous_date = fields.Datetime.now() - datetime.timedelta(days=30)

        self.fail_counter = (
            self.env["mail.mail"]
            .sudo()
            .search_count(
                [
                    ("date", ">=", previous_date),
                    ("state", "=", "exception"),
                ]
            )
        )

    def open_email_layout(self) -> dict:
        layout = self.env.ref("mail.mail_notification_layout", raise_if_not_found=False)
        if not layout:
            raise UserError(_("This layout seems to no longer exist."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Mail Layout"),
            "view_mode": "form",
            "res_id": layout.id,
            "res_model": "ir.ui.view",
        }

    def open_mail_templates(self) -> dict:
        return self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mail.action_email_template_tree_all"
        )
