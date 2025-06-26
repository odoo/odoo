# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"
    _description = "Stock Move Ewaybill"

    l10n_in_ewaybill_id = fields.One2many(related="picking_id.l10n_in_ewaybill_id")
    company_currency_id = fields.Many2one(related='company_id.currency_id')

    # Need to store values because we send it to the ewaybill and we need to keep the same value
    ewaybill_price_unit = fields.Monetary(
        compute='_compute_l10n_in_ewaybill_price_unit',
        currency_field='company_currency_id',
        store=True,
        readonly=False
    )
    ewaybill_tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        compute='_compute_l10n_in_tax_ids',
        store=True,
        readonly=False
    )

    @api.depends('l10n_in_ewaybill_id')
    def _compute_l10n_in_ewaybill_price_unit(self):
        for line in self:
            if line.l10n_in_ewaybill_id.state == 'pending' and line.picking_id.country_code == 'IN':
                line.ewaybill_price_unit = line._l10n_in_get_product_price_unit()

    @api.depends('l10n_in_ewaybill_id.fiscal_position_id')
    def _compute_l10n_in_tax_ids(self):
        for line in self:
            if line.l10n_in_ewaybill_id.state == 'pending' and line.picking_id.country_code == 'IN':
                taxes_details = line._l10n_in_get_product_tax()
                taxes = taxes_details['taxes']
                if taxes_details['is_from_order']:
                    # Don't map taxes if they are from sale/purchase order
                    line.ewaybill_tax_ids = taxes
                else:
                    if fiscal_position := line.l10n_in_ewaybill_id.fiscal_position_id:
                        taxes = fiscal_position.map_tax(taxes)
                    line.ewaybill_tax_ids = taxes.filtered_domain(
                        self.env['account.tax']._check_company_domain(self.company_id)
                    )
