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


def webclient_link(res_model, res_id):
    return u'/web#view_type=form&model={model}&id={id}'.format(model=res_model, id=res_id)


class AccountReportsConfiguratorController(Controller):

    @route('/account/reportconfigurator/<reportname>', type='http', auth='user', website=True)
    def configurator(self, reportname, **kwargs):
        if reportname == 'printjournal':
            template_name = 'account.report_journal'
        else:
            template_name = 'account.report_%s' % reportname
        configurator_obj = request.env['account.report.configurator']
        # record with only default values
        configurator_rec = configurator_obj.get_configurator(reportname).create({})
        report_sxw_dict = configurator_rec.to_report_sxw_dict(**kwargs)
        if 'print' in kwargs:
            response = request.make_response(None,
                headers=[('Content-Type', 'application/vnd.ms-excel'),
                         ('Content-Disposition', 'attachment; filename=table.xls;')])
            request.env['report.account.report_%s' % reportname].get_csv(report_sxw_dict, response)
            return response
        else:
            report_sxw_dict['webclient_link'] = webclient_link
            return request.make_response(request.env['report'].get_html(template_name, data=report_sxw_dict))

    @route('/account/reportconfigurator/download/<reportname>', type='http', auth='user', method="post", website=True)
    def htmltopdftoredirect(self, reportname, html=None):
        report_obj = request.registry['report']
        pdf = report_obj.get_pdf(request.cr, request.uid, [], reportname, html=html, context=request.context)
        pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
        return request.make_response(pdf, headers=pdfhttpheaders)
