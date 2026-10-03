from odoo import api, fields, models


class Website(models.Model):
    _inherit = 'website'

    l10n_ar_website_sale_show_both_prices = fields.Boolean(
        string="Display Price without National Taxes",
        compute='_compute_l10n_ar_website_sale_show_both_prices',
        readonly=False,
        store=True,
    )
    l10n_ar_final_consumer_limit = fields.Float(
        string="AR Final Consumer Max Amount",
        default=10_000_000,
        help="Order total, in company currency, above which a Consumidor Final must provide their DNI"
        " at checkout. Set by ARCA for sales to an unidentified Consumidor Final.",
    )

    @api.depends('company_id')
    def _compute_l10n_ar_website_sale_show_both_prices(self):
        for website in self:
            website.l10n_ar_website_sale_show_both_prices = (
                website.company_id.account_fiscal_country_id.code == 'AR'
            )
