# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"
    _description = "Stock Move Ewaybill"

    ewaybill_id = fields.Many2one(
        comodel_name='l10n.in.ewaybill')

    ewaybill_company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id')

    # Need to store values because we send it to the ewaybill and we need to keep the same value
    ewaybill_price_unit = fields.Monetary(
        compute='_compute_ewaybill_price_unit',
        currency_field='ewaybill_company_currency_id',
        store=True)
    ewaybill_tax_ids = fields.Many2many(
        comodel_name='account.tax',
        string="Taxes",
        compute='_compute_tax_ids',
        store=True)

    @api.depends('product_id.uom_id', 'product_id.standard_price', 'ewaybill_id')
    def _compute_ewaybill_price_unit(self):
        for line in self:
            if line.ewaybill_id:
                if line.ewaybill_id.state == 'pending':
                    line.ewaybill_price_unit = line.product_id.uom_id._compute_price(line.product_id.with_company(line.company_id).standard_price, line.product_uom)
            else:
                line.ewaybill_price_unit = 0

    @api.depends('product_id.supplier_taxes_id', 'product_id.taxes_id', 'ewaybill_id')
    def _compute_tax_ids(self):
        for line in self:
            if line.ewaybill_id:
                if line.ewaybill_id.state == 'pending':
                    company_domain = self.env['account.tax']._check_company_domain(self.company_id)
                    if line.picking_code == "incoming":
                        line.ewaybill_tax_ids = line._get_l10n_in_fiscal_position(line.product_id.supplier_taxes_id.filtered_domain(company_domain))
                    else:
                        line.ewaybill_tax_ids = line._get_l10n_in_fiscal_position(line.product_id.taxes_id.filtered_domain(company_domain))
            else:
                line.ewaybill_tax_ids = False

    def _get_l10n_in_fiscal_position(self, taxes):
        fiscal_position = self.env['account.chart.template'].ref('fiscal_position_in_inter_state', raise_if_not_found=False)
        if not fiscal_position:
            _logger.warning("""
                Fiscal position with ID fiscal_position_in_inter_state is not found in the system.
                In case of inter state transaction tax is not auto changed to IGST""")
        if fiscal_position and self.ewaybill_id.transaction_type == "inter_state":
            return fiscal_position.map_tax(taxes)
        else:
            return taxes
