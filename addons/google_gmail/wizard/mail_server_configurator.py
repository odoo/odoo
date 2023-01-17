# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MailServerConfigurator(models.TransientModel):
    _inherit = "mail.server.configurator"

    def action_setup(self):
        self.ensure_one()
        if self.server_type != "gmail_oauth":
            return super().action_setup()

        values = self._prepare_ir_mail_server_values()
        values["smtp_host"] = self.SMTP_HOSTS["gmail_oauth"]
        values["smtp_authentication"] = "gmail"
        smtp_server = self._create_ir_mail_server(values)

        if not self.is_only_outgoing:
            values = self._prepare_fetchmail_server_values()
            values["server"] = self.IMAP_HOSTS["gmail_oauth"]
            values["server_type"] = "gmail"
            imap_server = self.env["fetchmail.server"].create(values)

            # redirect to the incoming server at the end
            # because it will need to be confirmed
            return imap_server.open_google_gmail_uri()
        return smtp_server.open_google_gmail_uri()
