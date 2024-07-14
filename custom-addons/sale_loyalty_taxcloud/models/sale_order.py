# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from textwrap import shorten

from .taxcloud_request import TaxCloudRequest
from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.fields import Command

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_TaxCloudRequest(self, api_id, api_key):
        return TaxCloudRequest(api_id, api_key)

    def _update_programs_and_rewards(self, block=False):
        """Before we apply the discounts, we clean up any preset tax
           that might already since it may mess up the discount computation.
        """
        taxcloud_orders = self.filtered('fiscal_position_id.is_taxcloud')
        taxcloud_orders.order_line.write({'tax_id': [(Command.CLEAR,)]})
        return super()._update_programs_and_rewards()

    def _create_invoices(self, grouped=False, final=False, date=None):
        """Ensure that any TaxCloud order that has discounts is invoiced in one go.
           Indeed, since the tax computation of discount lines with Taxcloud
           requires that any negative amount of a coupon line be deduced from the
           lines it originated from, these cannot be invoiced separately as it be
           incoherent with what was computed on the order.
        """
        def not_totally_invoiceable(order):
            return any(
                line.qty_to_invoice != line.product_uom_qty
                and not line.is_downpayment
                for line in order.order_line
            )

        taxcloud_orders = self.filtered('fiscal_position_id.is_taxcloud')
        taxcloud_coupon_orders = taxcloud_orders.filtered('order_line.reward_id')
        partial_taxcloud_coupon_orders = taxcloud_coupon_orders.filtered(not_totally_invoiceable)
        if partial_taxcloud_coupon_orders:
            bad_orders = shorten(str(partial_taxcloud_coupon_orders.mapped('display_name'))[1:-1], 80, placeholder='...')
            raise UserError(_('Any order that has discounts and uses TaxCloud must be invoiced '
                              'all at once to prevent faulty tax computation with Taxcloud.\n'
                              'The following orders must be completely invoiced:\n%s', bad_orders))

        return super()._create_invoices(grouped=grouped, final=final, date=date)
