# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

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
