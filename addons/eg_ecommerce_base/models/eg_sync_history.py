from odoo import models, fields, api
from datetime import datetime, date, timedelta


class EgSyncHistory(models.Model):
    _name = "eg.sync.history"

    @api.model
    def set_date(self):
        return datetime.now()

    error_message = fields.Text(string="Abstract", readonly=True)
    name = fields.Char(string="Name", default="New")
    status = fields.Selection([('yes', 'Successful'),
                               ('no', 'Un-Successful'), ("partial", "Partial")], string='Status')
    process_on = fields.Selection([('product', 'Product'), ('customer', 'Customer'),
                                   ('order', 'Order'), ('category', 'Category'), ('attribute', 'Attribute')],
                                  string='Process On')
    process = fields.Selection([('a', 'Import'), ('b', 'Export'),
                                ('c', 'Update/Import'), ('d', 'Update/Export')], string='Process')
    create_date = fields.Datetime(string="Create Date", default=set_date, readonly=True)
    order_id = fields.Many2one(comodel_name="sale.order", string="Sale Order")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Customer")
    product_id = fields.Many2one(comodel_name="product.template", string="Product")
    instance_id = fields.Many2one(comodel_name="eg.ecom.instance", string="Instance")
    provider = fields.Selection(related="instance_id.provider", store=True)
    parent_id = fields.Boolean(string="Parent", default=False)
    child_id = fields.Boolean(string="Child", default=False)
    eg_history_id = fields.Many2one(comodel_name="eg.sync.history", string="Parent History", ondelete='cascade')
    eg_history_ids = fields.One2many(comodel_name="eg.sync.history", inverse_name="eg_history_id",
                                     string="Child History")

    # add by akash
    category_id = fields.Many2one(comodel_name="product.category", string="Category")
    attribute_id = fields.Many2one(comodel_name="product.attribute", string="Attribute")

    def unlink_history_by_cron(self):
        """
        In this method delete history record past 7 days
        :return: Don't return anything
        """
        past_week_date = date.today() - timedelta(days=7)
        past_week_date = past_week_date.strftime("%Y-%m-%d")
        eg_history_ids = self.search([("create_date", "<=", past_week_date), ("parent_id", "=", True)])
        if eg_history_ids:
            eg_history_ids.unlink()

    @api.model
    def create(self, vals):
        if not vals.get("name"):
            vals['name'] = self.env['ir.sequence'].next_by_code('eg.ecom.history') or "New"
        res = super(EgSyncHistory, self).create(vals)
        return res
