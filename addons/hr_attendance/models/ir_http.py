from openerp import models, service

class Http(models.Model):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(Http, self).session_info()
        result['is_employee'] = self.env.user.has_group('base.group_user')
        return result
