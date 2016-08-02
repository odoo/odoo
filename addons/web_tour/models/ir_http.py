from openerp import models
from openerp.http import request

class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(Http, self).session_info()
        if result['is_superuser']:
            result['web_tours'] = request.env['web_tour.tour'].get_consumed_tours()
        return result
