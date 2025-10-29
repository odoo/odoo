from odoo import api, fields, models


class Test_Read_Group_Override_Order(models.Model):
    _name = 'test_read_group_override.order'
    _description = 'Sales order'

    line_ids = fields.One2many('test_read_group_override.order.line', 'order_id')
    date = fields.Date()
    company_dependent_name = fields.Char(company_dependent=True)
    many2one_id = fields.Many2one('test_read_group_override.order')
    name = fields.Char()
    fold = fields.Boolean()

    @property
    def _order(self):
        if self.env.context.get('test_read_group_override_order_company_dependent'):
            return 'company_dependent_name'
        return super()._order


class Test_Read_Group_Override_OrderLine(models.Model):
    _name = 'test_read_group_override.order.line'
    _description = 'Sales order line'

    order_id = fields.Many2one('test_read_group_override.order')
    order_expand_id = fields.Many2one('test_read_group_override.order', group_expand='_read_group_expand_full')
    value = fields.Integer()
    date = fields.Date(related='order_id.date')
    