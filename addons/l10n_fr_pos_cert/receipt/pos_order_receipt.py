# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosOrderReceipt(models.AbstractModel):
    _inherit = 'pos.order.receipt'

    def _order_receipt_generate_line_data(self):
        lines_data = super()._order_receipt_generate_line_data()
        for line, line_data in zip(self.lines, lines_data):
            line_data['show_old_unit_price'] = self._show_old_unit_price(line)
        return lines_data

    def _show_old_unit_price(self, line):
        config = self.config_id
        discount_product = (
            config.discount_product_id
            # `discount_product_id` field is provided by `pos_discount`, so it may not exist.
            if config.module_pos_discount and hasattr(config, 'discount_product_id')
            else None
        )
        loyalty_trigger_products = (
            config._get_program_ids()
            .filtered(lambda p: p.program_type in ('gift_card', 'ewallet'))
            .trigger_product_ids
            # `_get_program_ids` method is provided by `pos_loyalty`, so it may not exist.
            if hasattr(config, '_get_program_ids')
            else self.env['product.product']
        )

        return (
            line.price_type == 'manual'
            and line.product_id != config.tip_product_id
            # `is_reward_line` field is provided by `pos_loyalty`, so it may not exist.
            and not (hasattr(line, 'is_reward_line') and line.is_reward_line)
            # `event_ticket_id` field is provided by `pos_event`, so it may not exist.
            and not (hasattr(line, 'event_ticket_id') and line.event_ticket_id)
            and line.product_id not in loyalty_trigger_products
            # `sale_order_origin_id` field is provided by `pos_sale`, so it may not exist.
            and not (hasattr(line, 'sale_order_origin_id') and line.sale_order_origin_id)
            and line.product_id != discount_product
        )
