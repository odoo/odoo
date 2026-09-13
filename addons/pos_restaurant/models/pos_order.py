from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    table_id = fields.Many2one(
        comodel_name="restaurant.table",
        index="btree_not_null",
        readonly=True,
        help="The table where this order was served",
    )
    customer_count = fields.Integer(
        string="Guests",
        readonly=True,
        help="The amount of customers that have been served by this order.",
    )
    course_ids = fields.One2many(
        comodel_name="restaurant.order.course",
        inverse_name="order_id",
        string="Courses",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ["table_id", "customer_count", "course_ids"]
        return params

    def _get_open_order(self, order):
        config_id = self.env["pos.session"].browse(order.get("session_id")).config_id
        if not config_id.module_pos_restaurant:
            return super()._get_open_order(order)

        domain = []
        if order.get("table_id", False) and order.get("state") == "draft":
            domain += [
                "|",
                ("uuid", "=", order.get("uuid")),
                "&",
                ("table_id", "=", order.get("table_id")),
                ("state", "=", "draft"),
            ]
        else:
            domain += [("uuid", "=", order.get("uuid"))]
        return self.env["pos.order"].search(domain, limit=1, order="id desc")

    def read_pos_data(self, data, config):
        result = super().read_pos_data(data, config)
        result["restaurant.order.course"] = (
            self.env["restaurant.order.course"]._load_pos_data_read(
                self.course_ids, config
            )
            if config
            else []
        )
        return result
