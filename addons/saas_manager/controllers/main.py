from odoo import http
from odoo.http import request

class SaasClientController(http.Controller):

    @http.route('/saas/create', type='http', auth='public', website=True)
    def saas_create_instance_form(self, **kwargs):
        return request.render('saas_manager.saas_client_create')
