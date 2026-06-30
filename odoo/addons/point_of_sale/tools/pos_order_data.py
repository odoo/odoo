

class PoSOrderData:
    """
    Convenience class which allow to easily compare 2 "orders datas" received from PoS ui
    """

    def __init__(self, order_data: dict):
        self.order_payment_value_sorted = tuple(sorted([(p[2]['amount'], p[2]['payment_method_id']) for p in order_data['statement_ids']]))
        self.order_received_lines_sorted = tuple(sorted([(l[2]['product_id'], l[2]['qty'], l[2]['price_unit']) for l in order_data['lines']]))

    def __hash__(self):
        return hash((
            self.order_received_lines_sorted,
            self.order_payment_value_sorted,
        ))
