from odoo import fields, models
from odoo.tools import format_list


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pk_edi_enable = fields.Boolean(related='company_id.l10n_pk_edi_enable', readonly=False)
    l10n_pk_edi_production_auth_token = fields.Char(related='company_id.l10n_pk_edi_production_auth_token', readonly=False)
    l10n_pk_edi_test_auth_token = fields.Char(related='company_id.l10n_pk_edi_test_auth_token', readonly=False)
    l10n_pk_edi_whitelisted = fields.Boolean(related='company_id.l10n_pk_edi_whitelisted')
    l10n_pk_edi_test_vat = fields.Char(related='company_id.l10n_pk_edi_test_vat', readonly=False)
    l10n_pk_edi_company_email = fields.Char(related='company_id.email', string="Authorized Email")

    def action_l10n_pk_edi_run_sandbox_tests(self):
        if failed_scenario_ids := self.company_id.l10n_pk_edi_run_test_scenarios():
            message = self.env._(
                "Please contact the Support Team for further details if these scenarios are required for your business. %(scenarios)s failed.",
                scenarios=format_list(self.env, failed_scenario_ids),
            )
            notif_type = 'warning'
        else:
            message = self.env._("All FBR sandbox scenarios passed.")
            notif_type = 'success'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': self.env._("FBR Sandbox Tests"),
                'message': message,
                'type': notif_type,
                'sticky': False,
            },
        }
