# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    outgoing_mail_server_type = fields.Selection(
        selection_add=[("outlook", "Outlook")],
        ondelete={"outlook": "set default"},
    )

    @api.model
    def _get_mail_server_values(self, server_type):
        values = super()._get_mail_server_values(server_type)
        if server_type == "outlook":
            values |= {
                "smtp_host": "smtp-mail.outlook.com",
                "smtp_authentication": "outlook",
            }
        return values

    @api.model
    def _get_mail_server_setup_end_action(self, smtp_server):
        if smtp_server.smtp_authentication == 'outlook':
            return smtp_server.sudo().open_microsoft_outlook_uri()
        return super()._get_mail_server_setup_end_action(smtp_server)
