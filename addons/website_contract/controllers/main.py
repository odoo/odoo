# -*- coding: utf-8 -*-

import openerp
from openerp.addons.web import http
from openerp.addons.web.http import request

class website_contract(http.Controller):

    @http.route(['/references/'], type='http', auth="public")
    def blog(self, **post):
        website = request.registry['website']
        partner_obj = request.registry['res.partner']
        account_obj = request.registry['account.analytic.account']

        project_ids = partner_obj.search(request.cr, openerp.SUPERUSER_ID, [('website_testimonial', "!=", False), ('website_published', '=', True)])

        if request.uid != website.get_public_user().id:
            contract_ids = account_obj.search(request.cr, openerp.SUPERUSER_ID, [(1, "=", 1)])
            for contract in account_obj.browse(request.cr, openerp.SUPERUSER_ID, contract_ids):
                if contract.partner_id:
                    project_ids.append(contract.partner_id.id)
            project_ids = list(set(project_ids))

        values = website.get_rendering_context({
            'partner_ids': partner_obj.browse(request.cr, openerp.SUPERUSER_ID, project_ids)
        })
        return website.render("website_contract.index", values)
