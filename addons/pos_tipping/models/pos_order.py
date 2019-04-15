# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    tip_amount = fields.Float(string='Tip Amount', compute='_compute_tip_amount', inverse='_set_tip_amount', help='The total amount tipped, this is computed using the configured tip product. This is the amount that will be captured when the session is closed.')
    is_tipped = fields.Boolean(string='Is Tipped', compute='_compute_is_tipped', help='Whether or not an order has been processed in the tipping interface.')
    is_tippable = fields.Boolean(string='Is Tippable', compute='_compute_is_tippable', help='Whether or not an order\'s tip can be changed.')
    is_being_captured = fields.Boolean(help='Technical field used to make sure we submit only one capture request for each order.')
    authorization_id = fields.Char(help='Technical field used to store the authorization ID for orders with an open tab.')
    authorization_payment_method_id = fields.Many2one('pos.payment.method', help='Payment method used to authorize this order')
    card_name = fields.Char(help='Technical field used to store the card name for orders with an open tab.')

    table_name = fields.Char(related='table_id.name', help='Used to easily load this in the POS.')
    partner_name = fields.Char(related='partner_id.name', help='Used to easily load this in the POS.')

    def _compute_tip_amount(self):
        for order in self:
            tip_product = order.config_id.tip_product_id
            lines = order.lines.filtered(lambda line: line.product_id == tip_product)
            order.tip_amount = sum(lines.mapped('price_subtotal_incl'))

    def _set_tip_amount(self):
        for order in self:
            if order.is_being_captured:
                raise ValidationError(_("Order %s is already being captured.") % order.name)
            order.is_being_captured = True

            tip_product = order.config_id.tip_product_id
            tip_line = order.lines.filtered(lambda line: line.product_id == tip_product)
            tip_line = tip_line[0] if tip_line else False

            if not tip_line:
                tip_line = self.env['pos.order.line'].create({
                    'order_id': order.id,
                    'name': 'Tip',
                    'product_id': tip_product.id,
                    'price_unit': order.tip_amount,
                    'price_subtotal': 0,  # will be calculated by _compute_amount_line_all
                    'price_subtotal_incl': 0,  # will be calculated by _compute_amount_line_all
                    'tax_ids': [(6, 0, [tip_product.taxes_id.id])] if tip_product.taxes_id else []
                })

            tip_line.qty = 1
            tip_line.price_unit = order.tip_amount

            new_amounts = tip_line._compute_amount_line_all()
            tip_line.write({
                'price_subtotal_incl': new_amounts['price_subtotal_incl'],
                'price_subtotal': new_amounts['price_subtotal']
            })

            order._onchange_amount_all()

            # update first non is_cash_count payment
            payment = order.payment_ids.filtered(lambda payment: payment.payment_method_id.use_payment_terminal)[0]
            payment.amount += order.tip_amount

    @api.depends('config_id.tip_product_id', 'lines')
    def _compute_is_tipped(self):
        for order in self:
            tip_product = order.config_id.tip_product_id
            order.is_tipped = any(order.lines.filtered(lambda line: line.product_id == tip_product))

    @api.depends('payment_ids')
    def _compute_is_tippable(self):
        for order in self:
            order.is_tippable = any(not payment_method.is_cash_count for payment_method in order.payment_ids.payment_method_id)

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        order_fields['authorization_id'] = ui_order.get('authorization_id')
        order_fields['authorization_payment_method_id'] = ui_order.get('authorization_payment_method_id')
        order_fields['card_name'] = ui_order.get('card_name')
        return order_fields

    @api.model
    def _get_table_draft_order_fields(self):
        res = super(PosOrder, self)._get_table_draft_order_fields()
        res += ['authorization_id', 'authorization_payment_method_id', 'card_name']
        return res

    @api.model
    def get_table_draft_orders(self, table_id):
        table_orders = super(PosOrder, self).get_table_draft_orders(table_id)

        for order in table_orders:
            if order['authorization_payment_method_id']:
                order['authorization_payment_method_id'] = order['authorization_payment_method_id'][0]

        return table_orders

    @api.model
    def set_tip(self, pos_reference, new_tip):
        order = self.search([('pos_reference', 'like', pos_reference)], limit=1)
        if not order:
            raise ValidationError(_('Reference %s does not exist.') % pos_reference)

        order.tip_amount = new_tip
        return True
