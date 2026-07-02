from odoo import _, fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pk_edi_enable = fields.Boolean(related='company_id.l10n_pk_edi_enable', readonly=False)
    l10n_pk_edi_first_time_setup = fields.Boolean(related='company_id.l10n_pk_edi_first_time_setup', readonly=False)
    l10n_pk_edi_test_environment = fields.Boolean(related='company_id.l10n_pk_edi_test_environment', readonly=False)
    l10n_pk_edi_production_auth_token = fields.Char(related='company_id.l10n_pk_edi_production_auth_token', readonly=False)
    l10n_pk_edi_test_auth_token = fields.Char(related='company_id.l10n_pk_edi_test_auth_token', readonly=False)
    l10n_pk_edi_test_vat = fields.Char(related='company_id.l10n_pk_edi_test_vat', readonly=False)
    l10n_pk_edi_test_vat_verified = fields.Selection(related='company_id.l10n_pk_edi_test_vat_verified', readonly=False)
    l10n_pk_edi_iap_server_ip = fields.Char(related='company_id.l10n_pk_edi_iap_server_ip')
    l10n_pk_edi_company_email = fields.Char(related='company_id.email', string='Authorized Email')

    def action_refresh_iap_server_ip(self):
        self.company_id.l10n_pk_edi_iap_server_ip = self.company_id._get_iap_server_ip()

    def action_l10n_pk_edi_run_sandbox_tests(self):
        logs = self.env['l10n_pk_edi.test.log'].run_test_scenarios()
        if not logs:
            return None
        return {
            'type': 'ir.actions.act_window',
            'name': 'FBR Sandbox Test Logs',
            'res_model': 'l10n_pk_edi.test.log',
            'view_mode': 'list',
            'domain': [('id', 'in', logs.ids)],
        }

    def action_l10n_pk_edi_view_company_test_logs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'FBR Sandbox Test Logs',
            'res_model': 'l10n_pk_edi.test.log',
            'view_mode': 'list',
            'domain': [('company_id', '=', self.company_id.id)],
        }

    def button_pk_edi_check_registration(self):
        auth_token = self.company_id.l10n_pk_edi_test_auth_token
        if not auth_token:
            raise UserError(_("Sandbox authentication token is missing. Please enter it before verifying."))
        params = {
            'auth_token': auth_token,
            'json_payload': {'Registration_No': self.l10n_pk_edi_test_vat},
        }
        result = self.env['iap.account']._l10n_pk_connect_to_server(
            False,
            params,
            '/api/l10n_pk_edi/1/registration',
        )
        if result.get('error'):
            raise UserError(result['error'].get('message', _('Unknown error')))
        self.company_id.l10n_pk_edi_test_vat_verified = result.get('REGISTRATION_TYPE', 'not_checked').lower()
