# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError

class TestModel(models.Model):
    _name = 'test_convert.test_model'
    _description = "Test Convert Model"

    usered_id = fields.Many2one('test_convert.usered')
    name = fields.Char()

    @api.model
    def action_test_date(self, today_date):
        return True

    @api.model
    def action_test_time(self, cur_time):
        return True

    @api.model
    def action_test_timezone(self, timezone):
        return True

class Usered(models.Model):
    _name = 'test_convert.usered'
    _description = "z test model ignore"

    name = fields.Char()
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    test_model_o2m_ids = fields.One2many('test_convert.test_model', 'usered_id')
    tz = fields.Char(default=lambda self: self.env.context.get('tz') or self.env.user.tz)

    @api.model
    def model_method(self, *args, **kwargs):
        return self, args, kwargs

    def method(self, *args, **kwargs):
        return self, args, kwargs

    def _load_records(self, data_list, update=False):
        context = self.env.context
        if context.get('install_filename') == 'test_convert_usered.xml':
            for data in data_list:
                values = data.get('values')
                if 'test_model_o2m_ids' in values and not values['test_model_o2m_ids']:
                    raise UserError("Null value in O2M When loading XML with sub records")
        return super()._load_records(data_list, update=update)
