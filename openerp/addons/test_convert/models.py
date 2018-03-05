from openerp import models

class TestModel(models.Model):
    _name = 'test_convert.test_model'

    def action_test_date(self, cr, uid, today_date):
        return True

    def action_test_time(self, cr, uid, cur_time):
        return True

    def action_test_timezone(self, cr, uid, timezone):
        return True
