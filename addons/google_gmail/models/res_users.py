# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    outgoing_mail_server_type = fields.Selection(
        selection_add=[("gmail", "Gmail")],
        ondelete={"gmail": "set default"},
    )

    @api.model
    def _get_mail_server_values(self, server_type):
        values = super()._get_mail_server_values(server_type)
        if server_type == "gmail":
            values |= {
                "smtp_host": "smtp.gmail.com",
                "smtp_authentication": "gmail",
            }
        return values

    @api.model
    def _get_mail_server_setup_end_action(self, smtp_server):
        if smtp_server.smtp_authentication == "gmail":
            return smtp_server.sudo().open_google_gmail_uri()
        return super()._get_mail_server_setup_end_action(smtp_server)
