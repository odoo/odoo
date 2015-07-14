# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.web.http import request
from openerp.osv import osv


class Report(osv.Model):
    _inherit = 'report'

    def render(self, cr, uid, ids, template, values=None, context=None):
        if request and hasattr(request, 'website'):
            if request.website is not None:
                request.session['report_view_ids'] = []
        return super(Report, self).render(cr, uid, ids, template, values=values, context=context)
