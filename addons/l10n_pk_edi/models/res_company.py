# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_pk_edi_pos_key = fields.Char(string="PoS ID", groups='base.group_system')
    l10n_pk_edi_token = fields.Char(string="E-invoice Token", groups='base.group_system')
    # This proxy is only to access FBR APIs from out side of Pakistan for testing purpose.
    # And will remove before stable release. (Use proxy server of USA and Dubai to access)
    l10n_pk_edi_proxy = fields.Char(string="HTTPS Proxy", groups='base.group_system')

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------

    def _l10n_pk_edi_export_check(self):
        self.ensure_one()
        errors = {}
        if not self.l10n_pk_edi_pos_key or not self.l10n_pk_edi_token:
            errors['l10n_pk_edi_company_value_missing'] = {
                'level': 'danger',
                'message': _("Configure the PoS Key and EDI Token to enable e-invoicing."),
                'action_text': _("Go to the configuration panel"),
                'action': self.env.ref('account.action_account_config').id,
            }
        if not self.l10n_pk_edi_proxy:
            errors['l10n_pk_edi_company_proxy_missing'] = {
                'level': 'danger',
                'message': _("Configure the Proxy Server(For Testing) to send request to FBR."),
                'action_text': _("Go to the configuration panel"),
                'action': self.env.ref('account.action_account_config').id,
            }
        return errors
