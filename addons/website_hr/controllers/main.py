# -*- coding: utf-8 -*-

from openerp.addons.web.http import request
from openerp.addons.website import website

class website_hr(website):

    @website.route(['/team'], type='http', auth="admin")
    def blog(self, cr, uid, **post):
        hr_obj = request.registry['hr.employee']

        employee_ids = hr_obj.search(cr, uid, [(1, "=", 1)])
        values = {
            'res_company': request.registry['res.company'].browse(cr, uid, 1),
            'employee_ids': hr_obj.browse(cr, uid, employee_ids),
        }

        html = self.render(cr, uid, "website_hr.index", values)
        return html
