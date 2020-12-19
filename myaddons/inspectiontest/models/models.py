# -*- coding: utf-8 -*-

from odoo import models, fields, api



class pltest(models.Model):
    _name = 'pltest.pltest'
    _description = 'pltest.pltest'

    description = fields.Char('材料编号', required=True)
    sender = fields.Char('选料人')
    date = fields.Datetime(string="选择时间", default=fields.Datetime.now)
    stye = fields.Char('型体')
    customer = fields.Char('客户货号')
    code = fields.Char('测试代号')
    supplier = fields.Char('供方')
    material = fields.Char('材料名称')
    qty = fields.Integer('数量')
    editor = fields.Html('editor')
    type = fields.Selection(selection=[('sample','样品'),('development','开发'),('production','批量')],string="测试性质",help="选择",default="sample")
    property_id = fields.One2many('qc.test.method', 'pltest_id', string='测试列表')
    # noteboook，一对多展示property中的数据

    is_expired = fields.Boolean(string="是否过期",compute="_compute_is_expired")

    @api.depends("date")
    def _compute_is_expired(self):
        print("hello")
        for rec in self:
            if rec.date:
                rec.is_expired = rec.date < fields.Datetime.now()
            else:
                rec.is_expired = False
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
    _name = 'qc.test.method'
    _description = 'qc.test.method'
    method= fields.Char('方法')
    property= fields.Char('测试项目')
    unit= fields.Char('单位')
    reqmt= fields.Char('指标')
    result= fields.Char('1样')
    pltest_id = fields.Many2one('pltest.pltest', string='第二部分')
