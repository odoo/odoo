from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_rate_domain(self, tax_group_id):
        if tax_group := self.env['account.chart.template'].ref(tax_group_id, raise_if_not_found=False):
            return [('tax_group_id', '=', tax_group.id)]
        return []

    l10n_fr_border_reference = fields.Char(string="Border Reference")
    l10n_fr_rate_id = fields.Many2one(
        comodel_name='account.tax',
        string="Rate",
        domain=lambda self: self._get_rate_domain('tax_group_sea_grant'),
    )
    l10n_fr_regional_rate_id = fields.Many2one(
        comodel_name='account.tax',
        string="Regional rate",
        domain=lambda self: self._get_rate_domain('tax_group_regional_sea_grant'),
    )
