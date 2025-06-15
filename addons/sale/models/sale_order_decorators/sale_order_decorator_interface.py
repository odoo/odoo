from odoo.addons.sale.models.sale_order_decorators.sale_order_logic_interface import SaleOrderLogicInterface


class SaleOrderDecoratorInterface(SaleOrderLogicInterface):
    def __init__(self, order, sale_order_logic_interface):
        super().__init__(order)
        self.child = sale_order_logic_interface


    def action_confirm(self):
        """ Confirm the given quotation(s) and set their confirmation date.

        If the corresponding setting is enabled, also locks the Sale Order.

        :return: True
        :rtype: bool
        :raise: UserError if trying to confirm cancelled SO's
        """
        self.child.action_confirm()


    def _action_cancel(self):
        """ Cancel SO after showing the cancel wizard when needed.

        only executed for post-cancel operations.
        """
        self.child._action_cancel()

    def _validate_order(self):
        """
        Confirm the sale order and send a confirmation email.

        :return: None
        """
        self.child._validate_order()


    def _recompute_prices(self):
        self.child._recompute_prices()