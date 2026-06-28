from odoo import api, fields, models


class TestToolsConvert(models.Model):
    _name = 'test_tools.convert'
    _description = 'Test Tools Convert'

    name = fields.Char(translate=True)
    usered_ids = fields.One2many('test_tools.convert.usered', 'test_id')

    @api.model
    def action_test_date(self, today_date):
        return True

    @api.model
    def action_test_time(self, cur_time):
        return True

    @api.model
    def action_test_timezone(self, timezone):
        return True


class TestToolsConvertUsered(models.Model):
    _name = 'test_tools.convert.usered'
    _description = 'Test Tools Convert Usered'

    name = fields.Char()
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    test_id = fields.Many2one('test_tools.convert')
    tz = fields.Char(default=lambda self: self.env.context.get('tz') or self.env.user.tz)

    @api.model
    def model_method(self, *args, **kwargs):
        return self, args, kwargs

    def method(self, *args, **kwargs):
        return self, args, kwargs
