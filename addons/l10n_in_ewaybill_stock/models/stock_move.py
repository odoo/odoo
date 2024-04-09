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
        compute='_compute_ewaybill_price_unit',
        currency_field='company_currency_id',
        store=True
    )
    ewaybill_tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        compute='_compute_tax_ids',
        store=True
    )

    @api.depends('product_id.uom_id', 'product_id.standard_price', 'l10n_in_ewaybill_id')
    def _compute_ewaybill_price_unit(self):
        for line in self.filtered(lambda line: line.l10n_in_ewaybill_id.state == 'pending'):
            line.ewaybill_price_unit = line.product_id.uom_id._compute_price(
                line.product_id.with_company(line.company_id).standard_price, line.product_uom
            )

    @api.depends('product_id.supplier_taxes_id', 'product_id.taxes_id', 'l10n_in_ewaybill_id')
    def _compute_tax_ids(self):
        for line in self.filtered(lambda line: line.l10n_in_ewaybill_id.state == 'pending'):
            taxes = (
                line.picking_code == "incoming" and
                line.product_id.supplier_taxes_id or line.product_id.taxes_id
            )
            line.ewaybill_tax_ids = line._get_l10n_in_fiscal_position(
                taxes.filtered_domain(self.env['account.tax']._check_company_domain(self.company_id))
            )

    def _get_l10n_in_fiscal_position(self, taxes):
        fiscal_position = self.env['account.chart.template'].ref('fiscal_position_in_inter_state', raise_if_not_found=False)
        if not fiscal_position:
            _logger.warning("""
                Fiscal position with ID fiscal_position_in_inter_state is not found in the system.
                In case of inter state transaction tax is not auto changed to IGST""")
        if fiscal_position and self.l10n_in_ewaybill_id.transaction_type == "inter_state":
            return fiscal_position.map_tax(taxes)
        return taxes
