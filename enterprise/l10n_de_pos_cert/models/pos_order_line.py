# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools.float_utils import float_repr


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    def prepare_line_data(self, is_adjusted, line_export_id):
        self.ensure_one()
        precision = self.currency_id.decimal_places
        business_type = self.get_fiskaly_business_type()
        if business_type == 'Forderungsentstehung':
            # Need an adjustment line to be added, send current line as normal sale
            business_type = 'Umsatz'
            is_adjusted = False
        vat_id = self.tax_ids_after_fiscal_position[0].get_vat_definition_id() if self.tax_ids_after_fiscal_position else 5  # no tax -> considered as non taxable

        # For settlement or deposit we will have qty 0 so won't get from the price_subtotal/price_subtotal_incl
        settlement_products = []
        if hasattr(self.order_id.config_id, 'settle_due_product_id'):
            settlement_products = [self.order_id.config_id.settle_due_product_id.id, self.order_id.config_id.settle_invoice_product_id.id, self.order_id.config_id.deposit_product_id.id]
        incl_vat = self.price_unit if self.product_id.id in settlement_products else self.price_subtotal_incl
        excl_vat = self.price_unit if self.product_id.id in settlement_products else self.price_subtotal

        line_vat_details = [self.order_id.session_id._get_vat_details(vat_id, incl_vat, excl_vat)]
        line_data = {
            'business_case': {
                'type': business_type,
                'amounts_per_vat_id': line_vat_details,
            },
            'lineitem_export_id': str(line_export_id),  # It should be unique and start over for each order from 1
            'storno': False,
            'text': self.full_product_name[:255],
            'item': {
                'number': str(self.product_id.id),
                'quantity': float_repr(self.qty or 1, precision),  # for settlement products qty comes 0
                'price_per_unit': float_repr(self.price_subtotal_incl, precision),
            },
        }

        # ID of redeemed voucher
        if hasattr(self, 'is_reward_line') and self.coupon_id:
            line_data['voucher_id'] = self.coupon_id.code

        # line discounts applied using numpad
        if self.discount:
            line_data['item']['discounts_per_vat_id'] = [{
                'vat_definition_export_id': vat_id,
                'incl_vat': float_repr(self._get_discount_amount(), precision),
            }]
        return line_data, is_adjusted

    def get_fiskaly_business_type(self):
        self.ensure_one()
        config = self.order_id.config_id
        # tips
        if config.iface_tipproduct and self.product_id == config.tip_product_id:
            # VAT export ID 5 indicates that the item falls under non taxable grid considered as provided to an employee
            if not self.product_id.taxes_id or self.product_id.taxes_id[0].get_vat_definition_id() == 5:
                return 'TrinkgeldAN'  # tip to employee
            return 'TrinkgeldAG'  # tip under employer

        # discount
        if config.module_pos_discount and self.product_id.id == config.discount_product_id.id:
            return 'Rabatt'

        # Multipurpose Vouchers
        if hasattr(self, 'is_reward_line'):  # loyalty enabled
            if self.coupon_id and self.coupon_id.program_type in ['gift_card', 'ewallet']:
                return 'MehrzweckgutscheinEinloesung'  # redemption
            if self.product_id.id in self.env['loyalty.program'].search([
                    ('pos_ok', '=', True),
                    '|', ('pos_config_ids', 'in', config.id), ('pos_config_ids', '=', False),
                    ('program_type', 'in', ['gift_card', 'ewallet'])
                ]).trigger_product_ids.ids:
                return 'MehrzweckgutscheinKauf'  # sale

        # down payments
        if hasattr(config, 'down_payment_product_id'):
            if self.sale_order_origin_id:
                return 'Anzahlungseinstellung'  # down payment
            if self.order_id.refunded_order_id and self.refunded_orderline_id.sale_order_origin_id:
                return 'Anzahlungsaufloesung'  # down payment liquidation

        if hasattr(config, 'settle_due_product_id'):  # settle due installed
            # receivable account deposites
            # work similar to MPGV sale for all kind of incoming money to customer account
            if self.product_id.id in [config.deposit_product_id.id, config.settle_due_product_id.id]:
                return 'MehrzweckgutscheinKauf'

            # formerly created invoiced receivables are settled through PoS
            if self.product_id.id == config.settle_invoice_product_id.id:
                return 'Forderungsaufloesung'

        # order paid using payment method that has no journal set (receivable account) (partial or full payment)
        if self.order_id.payment_ids.filtered(lambda p: not p.payment_method_id.journal_id):
            # change the type based on invoiced (Forderungsentstehung) or not (MehrzweckgutscheinEinloesung)
            # at time of adjustment line creation otherwise won't be able to differentiate normal MPGV used or case of adjustment
            return 'Forderungsentstehung'

        # normal sale
        return 'Umsatz'
