# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailServerConfigurator(models.TransientModel):
    _inherit = "mail.server.configurator"

    is_mass_mailing_default = fields.Boolean(
        "Mass Mailing Default",
        help="The mail server will be used by default by mass mailing",
    )

    def _create_ir_mail_server(self, values):
        self.ensure_one()
        smtp_server = super()._create_ir_mail_server(values)

        if self.is_mass_mailing_default:
            Config = self.env["ir.config_parameter"].sudo()
            Config.set_param("mass_mailing.outgoing_mail_server", True)
            Config.set_param("mass_mailing.mail_server_id", smtp_server.id)

        return smtp_server
