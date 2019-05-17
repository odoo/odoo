from odoo import api, models

class TestModel(models.Model):
    _name = 'test_convert.test_model'
    _description = "Test Convert Model"

    @api.model
    def action_test_date(self, today_date):
        return True

    @api.model
    def action_test_time(self, cur_time):
        return True

    @api.model
    def action_test_timezone(self, timezone):
        return True
