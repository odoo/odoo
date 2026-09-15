from odoo import api, fields, models

TEST_PROVIDER_SMTP_HOST = "smtp.test-provider.example.com"


class IrMail_Server(models.Model):
    _inherit = "ir.mail_server"

    smtp_authentication = fields.Selection(
        selection_add=[("test_provider", "Test Provider")],
        ondelete={"test_provider": "set default"},
    )


class ResUsers(models.Model):
    _inherit = "res.users"

    outgoing_mail_server_type = fields.Selection(
        selection_add=[("test_provider", "Test Provider")],
        ondelete={"test_provider": "set default"},
    )

    @api.model
    def _prepare_mail_server_vals(self, server_type):
        values = super()._prepare_mail_server_vals(server_type)
        if server_type == "test_provider":
            values |= {
                "smtp_host": TEST_PROVIDER_SMTP_HOST,
                "smtp_authentication": "test_provider",
            }
        return values
