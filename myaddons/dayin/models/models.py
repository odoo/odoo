# -*- coding: utf-8 -*-

from odoo import models, fields, api


class property_dayin(models.Model):
    _name = 'property.dayin'
    _description = 'property.dayin'
    method= fields.Char('方法')
    property= fields.Char('测试项目')
    unit= fields.Char('单位')
    reqmt= fields.Char('指标')
    result= fields.Char('1样')


    def _get_date(self):
        sql = "select * form property_dayin;"
        self._cr.execute(sql)
        return self._cr.fetchall()

    @api.model
    def get_report_values(self,docids,data=None):

        return self._get_data(docids)

    def test2(self):
        print(111)
