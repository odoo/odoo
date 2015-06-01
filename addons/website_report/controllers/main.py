# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.website.controllers.main import Website
from openerp.http import request, route


class Website(Website):

    @route()
    def customize_template_get(self, key, full=False, bundles=False):
        res = super(Website, self).customize_template_get(key, full=full, bundles=bundles)
        if full:
            for r in request.session.get('report_view_ids', []):
                res += super(Website, self).customize_template_get(r.get('xml_id'), full=full)
        return res
