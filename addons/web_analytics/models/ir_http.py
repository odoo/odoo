from openerp import models, service

class Http(models.Model):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(Http, self).session_info()
        result['version_info'] = service.common.exp_version()
        return result
