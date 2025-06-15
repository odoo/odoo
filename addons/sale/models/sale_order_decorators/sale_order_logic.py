from odoo.exceptions import UserError
from odoo.addons.sale.models.sale_order_decorators.sale_order_logic_interface import SaleOrderLogicInterface


class SaleOrderLogic(SaleOrderLogicInterface):
    def __init__(self, orders):
        super().__init__(orders)

    def action_confirm(self):
        """ Confirm the given quotation(s) and set their confirmation date.

        If the corresponding setting is enabled, also locks the Sale Order.

        :return: True
        :rtype: bool
        :raise: UserError if trying to confirm cancelled SO's
        """
        orders = self.orders
        for order in orders:
            error_msg = order._confirmation_error_message()
            if error_msg:
                raise UserError(error_msg)

        orders.order_line._validate_analytic_distribution()

        for order in orders:
            if order.partner_id in order.message_partner_ids:
                continue
            order.message_subscribe([order.partner_id.id])

        orders.write(orders._prepare_confirmation_values())

        # Context key 'default_name' is sometimes propagated up to here.
        # We don't need it and it creates issues in the creation of linked records.
        context = orders._context.copy()
        context.pop('default_name', None)

        orders.with_context(context)._action_confirm()
        user = orders[:1].create_uid
        if user and user.sudo().has_group('sale.group_auto_done_setting'):
            # Public user can confirm SO, so we check the group on any record creator.
            orders.action_lock()

        if orders.env.context.get('send_email'):
            orders._send_order_confirmation_mail()

        return True

    def _action_cancel(self):
        """ Cancel SO after showing the cancel wizard when needed.

        only executed for post-cancel operations.
        """
        orders = self.orders
        inv = orders.invoice_ids.filtered(lambda inv: inv.state == 'draft')
        inv.button_cancel()
        return orders.write({'state': 'cancel'})

    def _validate_order(self):
        """
        Confirm the sale order and send a confirmation email.

        :return: None
        """
        # TODO: Untested
        orders = self.orders
        orders.with_context(send_email=True).action_confirm()

    def _recompute_prices(self):
        orders = self.orders
        lines_to_recompute = orders._get_update_prices_lines()
        lines_to_recompute.invalidate_recordset(['pricelist_item_id'])
        lines_to_recompute.with_context(force_price_recomputation=True)._compute_price_unit()
        # Special case: we want to overwrite the existing discount on _recompute_prices call
        # i.e. to make sure the discount is correctly reset
        # if pricelist rule is different than when the price was first computed.
        lines_to_recompute.discount = 0.0
        lines_to_recompute._compute_discount()
        orders.show_update_pricelist = False