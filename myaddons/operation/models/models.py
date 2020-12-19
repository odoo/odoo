# -*- coding: utf-8 -*-

from odoo import models, fields, api


class operation(models.Model):
    _name = 'operation.operation'
    _description = 'operation.operation'

    name = fields.Char()
    value = fields.Integer()
    value2 = fields.Float(compute="_value_pc", store=True)
    description = fields.Text()
    is_expired = fields.Boolean(string="是否出库",default=False)

    @api.model
    def report_missing_book(self):
        print(111)

    @api.model
    def change_is_expired(self):
        for order in self:
            order.is_expired = not order.is_expired


    @api.depends('value')
    def _value_pc(self):
        for record in self:
            record.value2 = float(record.value) / 100

    def test(self):
        for order in self:
            order.unlink()


    @api.model
    def test2(self):
        for order in self:
            order.unlink()

    @api.model
    def funcname(self):
        vals_list = [{'name': '100','value': '200','value2': '200'}]
        result = super(operation, self).create(vals_list)
        return result
        # orders = [order for order in self.browse(context.get('active_ids'))]

        # print(orders)

    @api.model
    def funupdate(self):
        vals_list = [{'name': '100', 'value': '200', 'value2': '200'}]
        result = super(operation, self).create(vals_list)
        return result

    @api.model
    def funupdate2(self):
        for i in self:
            print(i.name)

    @api.model
    def test_test(self):
        for i in self:
            print(i.id)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'operation.operation',
            # 'limit':1,
            'name': 'xxtr window',
            'multi': True,
            'auto_refresh': 1,
            # 'view_type': 'form',
            # 设置过滤条件search_default_+所需判断的字段名
            # 'context': {'search_default_name': value},
            'view_mode': 'form',
            # 'views': [(True, "tree")],
            'target': 'new',
            'auto_search': True,
        }

    @api.model
    def test_delect(self):
        for order in self:
            order.unlink()

    @api.model
    def button_sheet_id(self):
        print(111)






#这里写入
    @api.model
    def change_form(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'operation.operation',
            # 'limit':1,
            'name': 'xxtr window',
            'multi': True,
            'auto_refresh': 1,
            # 'view_type': 'form',
            # 设置过滤条件search_default_+所需判断的字段名
            # 'context': {'search_default_name': value},
            'view_mode': 'form',
            # 'views': [(True, "tree")],
            'target': 'new',
            'auto_search': True,
        }


class ShowMessageWizard(models.TransientModel):
    _name = "message.wizard"
    _description = "提示一下"

    def say_hello(self):
        context = dict(self._context or {})
        view_type = context.get('view_type')
        actived_id = context.get('actived_id')
        active_ids = context.get('active_ids')
        print("视图类型：", view_type)
        if view_type == "form":
            print("Form Selected ID:", actived_id)
        elif view_type == "list":
            print("Tree Selected IDs:", active_ids)
        else:
            print("其他视图类型的ID在JS里自行传值吧。")
        print("接下来做你想做的")