from odoo import http
from odoo.http import request


class MdMasterCoaController(http.Controller):

    @http.route('/md_master_coa/manual', auth='user', website=False)
    def coa_manual(self, **kwargs):
        return request.render('md_master_coa.template_md_coa_manual', {})
