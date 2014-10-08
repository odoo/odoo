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

from openerp.addons.web.http import Controller, route, request


class AccountReportsConfiguratorController(Controller):

    @route('/account/reportconfigurator/<reportname>', type='http', auth='user', website=True)
    def configurator(self, reportname, **kwargs):
        html = request.env['report'].get_html(
            request.env['account.account'].search([], limit=0), 'account.report_%s' % reportname,
            data=request.env['account.report.configurator'].get_configurator(reportname).create({}).to_report_sxw_dict(**kwargs)
        )
        return request.make_response(html)
