from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_es_simplified_invoice_limit = fields.Float(
        string="Simplified Invoice limit amount",
        help="Over this amount is not legally possible to create a simplified invoice",
        default=400,
    )

    l10n_es_general_chart_type = fields.Selection(
        selection=[
            ('smes', 'SMES'),
            ('full', 'Completo'),
            ('abbreviated', 'Abreviado')
        ],
        string="Individual or Company",
        help="Select which accounting plan do you wish to apply",
        default='smes'
    )

    l10n_es_tax_plan = fields.Selection(
        selection=[
            ('aeat', 'AEAT'),
            ('hacienda_foral_bizkaia', 'Hacienda Foral Bizkaia'),
            ('hacienda_foral_gipuzkoa', 'Hacienda Foral Guipuzkoa'),
            ('hacienda_foral_alava', 'Hacienda Foral Álava'),
            ('igic', 'IGIC (Canarias)'),
            ('ipsi', 'IPSI (Ceuta y Melilla)'),
        ],
        string="Hacienda",
        help="Select tax plan",
        default='aeat'
    )

    real_estate = fields.Boolean('Real Estate')
    intracomunitary_oss = fields.Boolean('Intracomunitary, Oss')
    reagyp = fields.Boolean('REAGYP')

    def write(self, vals):
        res = super().write(vals)
        if 'l10n_es_general_chart_type' in vals or 'l10n_es_tax_plan' in vals:
            for company in self:
                template = self.env['account.chart.template'].with_company(company)
                template._l10n_es_manage_dynamic_accounts(company)
                template._l10n_es_manage_dynamic_taxes(company)
        return res
