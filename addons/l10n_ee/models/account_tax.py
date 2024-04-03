from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_ee_kmd_inf_code = fields.Selection(
        selection=[
            ('1', 'Sale KMS §41/42'),
            ('2', 'Sale KMS §41^1'),
            ('11', 'Purchase KMS §29(4)/30/32'),
            ('12', 'Purchase KMS §41^1'),
        ],
        string='KMD INF Code',
        default=False,
        help='This field is used for the comments/special code column in the KMD INF report.'
    )


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    l10n_ee_kmd_inf_code = fields.Selection(
        selection=[
            ('1', 'Sale KMS §41/42'),
            ('2', 'Sale KMS §41^1'),
            ('11', 'Purchase KMS §29(4)/30/32'),
            ('12', 'Purchase KMS §41^1'),
        ],
        string='KMD INF Code',
        default=False,
        help='This field is used for the comments/special code column in the KMD INF report.'
    )

    def _get_tax_vals(self, company, tax_template_to_tax):
        # OVERRIDE
        vals = super()._get_tax_vals(company, tax_template_to_tax)
        vals.update({
            'l10n_ee_kmd_inf_code': self.l10n_ee_kmd_inf_code,
        })
        return vals
