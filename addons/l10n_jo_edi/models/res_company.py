import requests

from odoo import fields, models

JOFOTARA_URL = "https://backend.jofotara.gov.jo/core/invoices/"


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_jo_edi_sequence_income_source = fields.Char(string="JoFotara Sequence of Income Source")
    l10n_jo_edi_secret_key = fields.Char(string="JoFotara Secret Key", groups="base.group_system")
    l10n_jo_edi_client_identifier = fields.Char(string="JoFotara Client ID", groups="base.group_system")
    l10n_jo_edi_taxpayer_type = fields.Selection(string="JoFotara Taxpayer Type", selection=[
        ('income', "Unregistered in the sales tax"),
        ('sales', "Registered in the sales tax"),
        ('special', "Registered in the special sales tax"),
    ], default='sales')
    l10n_jo_edi_demo_mode = fields.Boolean(string="JoFotara Demo Mode")

    def _l10n_jo_validate_config(self):
        self.ensure_one()
        error_msgs = []
        if not self.sudo().l10n_jo_edi_client_identifier:
            error_msgs.append(self.env._("Client ID is missing."))
        if not self.sudo().l10n_jo_edi_secret_key:
            error_msgs.append(self.env._("Secret key is missing."))
        if not self.l10n_jo_edi_taxpayer_type:
            error_msgs.append(self.env._("Taxpayer type is missing."))
        if not self.l10n_jo_edi_sequence_income_source:
            error_msgs.append(self.env._("Activity number (Sequence of income source) is missing."))

        if error_msgs:
            return self.env._("%s \nTo set: Configuration > Settings > Electronic Invoicing (Jordan)", "\n".join(error_msgs))

    def _l10n_jo_build_jofotara_headers(self):
        self.ensure_one()
        return {
            'Client-Id': self.sudo().l10n_jo_edi_client_identifier,
            'Secret-Key': self.sudo().l10n_jo_edi_secret_key,
        }

    def _send_l10n_jo_edi_request(self, params, headers):
        if self.l10n_jo_edi_demo_mode:
            return {'EINV_QR': "Demo JoFotara QR"}  # mocked response

        try:
            response = requests.post(JOFOTARA_URL, json=params, headers=headers, timeout=50)
        except requests.exceptions.Timeout:
            return {'error': self.env._("Request timeout! Please try again.")}
        except requests.exceptions.RequestException as e:
            return {'error': self.env._("Invalid request: %s", e)}

        if not response.ok:
            content = response.content.decode()
            if response.status_code == 403:
                content = self.env._("Access forbidden. Please verify your JoFotara credentials.")
            return {'error': self.env._("Request failed: %s", content)}
        dict_response = response.json()
        return dict_response
