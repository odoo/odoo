from markupsafe import Markup

from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MailGatewayAllowed(models.Model):
    _name = "mail.gateway.allowed"
    _description = "Mail Gateway Allowed"

    email = fields.Char(
        string="Email Address",
        required=True,
    )
    email_normalized = fields.Char(
        string="Normalized Email",
        compute="_compute_email_normalized",
        store=True,
        index=True,
    )

    @api.depends("email")
    def _compute_email_normalized(self) -> None:
        for record in self:
            record.email_normalized = tools.email_normalize(record.email)

    @api.constrains("email")
    def _check_email_normalizes(self) -> None:
        for record in self:
            if not tools.email_normalize(record.email):
                _debug.logic(
                    "email_rejected", record=record.id, reason="not_normalizable"
                )
                raise ValidationError(_("Invalid email address “%s”", record.email))

    @api.model
    def get_empty_list_help(self, help_message: str) -> str:
        icp = self.env["ir.config_parameter"]
        LOOP_MINUTES = icp._get_int_param("mail.gateway.loop.minutes", 120)
        LOOP_THRESHOLD = icp._get_int_param("mail.gateway.loop.threshold", 20)

        return Markup(
            _("""
            <p class="o_view_nocontent_smiling_face">
                Add addresses to the Allowed List
            </p><p>
                To protect you from spam and reply loops, Odoo automatically blocks emails
                coming to your gateway past a threshold of <b>%(threshold)i</b> emails every <b>%(minutes)i</b>
                minutes. If there are some addresses from which you need to receive very frequent
                updates, you can however add them below and Odoo will let them go through.
            </p>""")
        ) % {
            "threshold": LOOP_THRESHOLD,
            "minutes": LOOP_MINUTES,
        }
