from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    income_tax_id = fields.Char(related='partner_id.l10n_sk_dic', string='DIČ', readonly=False)
    peppol_validation_token = fields.Char(
        groups="account.group_account_manager",
        help="Verification token used to authenticate the user.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        # The partner is created before the company, so when the income_tax_id is False, it overwrites the partner's DIČ
        for vals in vals_list:
            if not vals.get('income_tax_id'):
                vals.pop('income_tax_id', None)
        return super().create(vals_list)
