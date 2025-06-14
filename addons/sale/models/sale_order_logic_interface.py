from abc import abstractmethod


class SaleOrderLogicInterface:
    def __init__(self, orders):
        self.orders = orders

    @abstractmethod
    def action_confirm(self):
        """ Confirm the given quotation(s) and set their confirmation date.

        If the corresponding setting is enabled, also locks the Sale Order.

        :return: True
        :rtype: bool
        :raise: UserError if trying to confirm cancelled SO's
        """
        ...

    @abstractmethod
    def _action_cancel(self):
        """ Cancel SO after showing the cancel wizard when needed.

        only executed for post-cancel operations.
        """
        ...

    @abstractmethod
    def _validate_order(self):
        """
        Confirm the sale order and send a confirmation email.

        :return: None
        """
        ...

    @abstractmethod
    def _recompute_prices(self):
        ...