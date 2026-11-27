# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.l10n_np.tools.bikram_sambat import convert_ad_to_bs_with_formatting


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_np_customs_declaration_number = fields.Char(
        string="Customs Declaration Number",
        tracking=True,
        help="A unique tracking code assigned to each commercial or personal import/export shipment processed through the Department of Customs.",
    )
    l10n_np_fiscal_date = fields.Char(
        string="Date in Nepal",
        compute="_compute_l10n_np_fiscal_date",
        help="Bikram Sambat (BS) date for Nepal.",
    )

    def _l10n_np_format_date(self, date_val):
        date_val = fields.Date.to_date(date_val)
        if not date_val:
            return ""
        lang = self.env['res.lang']._lang_get(self.env.lang or 'en_US')
        date_format = lang.date_format if lang else '%m/%d/%Y'
        try:
            return convert_ad_to_bs_with_formatting(date_val, date_format)[1]
        except ValueError:
            return ""

    @api.depends('invoice_date', 'date', 'move_type', 'company_id')
    def _compute_l10n_np_fiscal_date(self):
        for move in self:
            if move.country_code == 'NP':
                move_date = move.invoice_date if move.is_invoice(include_receipts=True) else move.date
                move.l10n_np_fiscal_date = move._l10n_np_format_date(move_date)
            else:
                move.l10n_np_fiscal_date = ""
