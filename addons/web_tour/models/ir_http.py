from openerp import models
from openerp.http import request


class Http(models.Model):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(Http, self).session_info()
        if result['is_admin']:
            consumed_tours = request.env['web_tour.tour'].search([('user_id', '=', request.env.uid)])
            result['web_tours'] = [t.name for t in consumed_tours]
        return result
