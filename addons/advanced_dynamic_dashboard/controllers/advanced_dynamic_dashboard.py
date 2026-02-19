# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import http
from odoo.http import request


class DynamicDashboard(http.Controller):
    """Class to search and filter values in dashboard"""

    @http.route('/tile/details', type='json', auth='user')
    def tile_details(self, **kw):
        """Function to get tile details"""
        tile_id = request.env['dashboard.block'].sudo().browse(int(kw.get('id')))
        if tile_id:
            return {'model': tile_id.model_id.model, 'filter': tile_id.filter,
                    'model_name': tile_id.model_id.name}
        else:
            return False

    @http.route('/custom_dashboard/search_input_chart', type='json',
                auth="public", website=True)
    def dashboard_search_input_chart(self, search_input):
        """Function to filter search input in dashboard"""
        return request.env['dashboard.block'].search([
            ('name', 'ilike', search_input)]).ids
