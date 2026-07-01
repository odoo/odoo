from odoo import models, fields, api
from datetime import datetime, date


class EgEComInstance(models.Model):
    _name = "eg.ecom.instance"

    @api.model
    def set_date(self):
        return datetime.now()

    provider = fields.Selection([], string="Provider")
    name = fields.Char(string="Name")
    url = fields.Char(string="URL")
    user_id = fields.Many2one(comodel_name="res.users", string="User", default=lambda self: self.env.user.id)
    inventory_location_id = fields.Many2one(comodel_name="eg.inventory.location", string="Inventory Location")
    active = fields.Boolean(string="Active", default=True)
    create_date = fields.Datetime(string="Create Date", default=set_date)
    connection_message = fields.Char(string="Connection Message")
    color = fields.Integer(string="Color Index")
    mapped_order_count = fields.Integer(string="Mapped Order Count", compute="_compute_for_all_count")
    mapped_product_count = fields.Integer(string="Mapped Product Count", compute="_compute_for_all_count")
    update_product_count = fields.Integer(string="Update Product Count", compute="_compute_for_all_count")
    export_product_count = fields.Integer(string="Export Product Count", compute="_compute_for_all_count")

    # add by akash
    eg_product_pricelist_id = fields.Many2one(comodel_name='eg.product.pricelist',
                                              string="eCom Product PriceList")

    def _compute_for_all_count(self):
        for rec in self:
            mapped_product_ids = self.env["eg.product.template"].search(
                [("inst_product_tmpl_id", "not in", ["", False]), ("update_required", "=", False),
                 ("instance_id", "=", rec.id)])
            update_product_ids = self.env["eg.product.template"].search(
                [("inst_product_tmpl_id", "not in", ["", False]), ("update_required", "=", True),
                 ("instance_id", "=", rec.id)])
            export_product_ids = self.env["eg.product.template"].search(
                [("inst_product_tmpl_id", "in", ["", False]), ("update_required", "=", True),
                 ("instance_id", "=", rec.id)])
            mapped_order_ids = self.env["eg.sale.order"].search(
                [("inst_order_id", "not in", ["", False]), ("update_required", "=", False),
                 ("instance_id", "=", rec.id)])
            rec.mapped_order_count = len(mapped_order_ids)
            rec.mapped_product_count = len(mapped_product_ids)
            rec.update_product_count = len(update_product_ids)
            rec.export_product_count = len(export_product_ids)

    def test_connection_of_instance(self, from_cron=None):
        return

    def cron_for_test_connection(self):
        instance_ids = self.search([])
        for instance_id in instance_ids:
            instance_id.test_connection_of_instance()

    # @api.model
    # def create_sequence_for_ecom_history(self):
    #     self.env["ir.sequence"].create({"name": "eCom Integration",
    #                                     "code": "eg.ecom.history",
    #                                     "prefix": "ECH",
    #                                     "padding": 4,
    #                                     "number_increment": 1})
