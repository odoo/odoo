# -*- coding: utf-8 -*-

from odoo import models, fields, api


class first_test(models.Model):
    _name = 'first_test.first_test'
    _description = 'first_test.first_test'

    description = fields.Char('材料编号', required=True)
    sender = fields.Char('选料人')
    date = fields.Datetime(string="选择时间", default=fields.Datetime.now)
    stye = fields.Char('型体')
    customer = fields.Char('客户货号')
    code = fields.Char('测试代号')
    supplier = fields.Char('供方')
    material = fields.Char('材料名称')
    qty = fields.Integer('数量')
    # editor = fields.Html('editor')
    type = fields.Selection(selection=[('sample', '样品'), ('development', '开发'), ('production', '批量')], string="测试性质",
                            help="选择", default="sample")
    property_id = fields.One2many('first.test.method', 'pltest_id', string='测试列表')

    @api.model
    def add_product_control(self):
        pass

    @api.model
    def add_section_control(self):
        pass

    @api.model
    def add_note_control(self):
        pass

    class property(models.Model):
        _name = 'first.test.method'
        _description = 'first.test.method'
        method = fields.Selection(selection=[('psp-06', 'v1'), ('psp-03', 'v2'), ('pst-21', 'v1a')], string="方法",
                            help="选择", default="psp-06")
        property = fields.Char('测试项目')
        unit = fields.Char('单位')
        reqmt = fields.Char('指标')
        result = fields.Char('1样')
        pltest_id = fields.Many2one('first_test.first_test', string='第二部分')
        # Many2Mangy
        # comodel_name – 在关联字段及字段继承以外的情况下必填的目标目标模型（字符串）名
        # relation(str) – 数据库中存储关联的可选数据表名称（用Many2Many后数据库会新建一张表）
        # column1(str) – 在relation数据表中引用“当前模型”记录的可选列名
        # column2(str) – 在relation数据表中引用“关联模型”记录的可选列名
        first_test_ids = fields.Many2many('first_test.first_test','first_test_method','property','description',)
