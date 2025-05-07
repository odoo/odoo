from odoo import api, fields, models


class Website(models.Model):
    _inherit = 'website'

    l10n_ar_website_sale_show_both_prices = fields.Boolean(
        string="Display Price without National Taxes",
        compute='_compute_l10n_ar_website_sale_show_both_prices',
        readonly=False,
        store=True,
    )

    @api.depends('company_id')
    def _compute_l10n_ar_website_sale_show_both_prices(self):
        for website in self:
            website.l10n_ar_website_sale_show_both_prices = (
                website.company_id.account_fiscal_country_id.code == 'AR'
            )

    @api.depends('company_id.account_fiscal_country_id')
    def _compute_show_line_subtotals_tax_selection(self):
        # EXTENDS 'website_sale'
        super()._compute_show_line_subtotals_tax_selection()
        for website in self:
            if website.company_id.account_fiscal_country_id.code == 'AR':
                website.show_line_subtotals_tax_selection = 'tax_included'
