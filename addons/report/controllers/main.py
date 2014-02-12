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

from openerp.addons.web import http
from openerp.addons.web.http import request

import logging


_logger = logging.getLogger(__name__)


class Report(http.Controller):

    @http.route(['/report/<reportname>/<docids>'], type='http', auth='user', website=True, multilang=True)
    def report_html(self, reportname, docids, **kwargs):
        """This is the generic route for QWeb reports. It is used for reports
        which do not need to preprocess the data (i.e. reports that just display
        fields of a record).

        It is given a ~fully qualified report name, for instance 'account.report_invoice'.
        Based on it, we know the module concerned and the name of the template. With the
        name of the template, we will make a search on the ir.actions.reports.xml table and
        get the record associated to finally know the model this template refers to.

        There is a way to declare the report (in module_report(s).xml) that you must respect:
            id="action_report_model"
            model="module.model"  # To know which model the report refers to
            string="Invoices"
            report_type="qweb-pdf"  # or qweb-html
            name="module.template_name"
            file="module.template_name"

        If you don't want your report to be listed under the print button, just add
        'menu=False'.
        """
        ids = [int(i) for i in docids.split(',')]
        ids = list(set(ids))
        report = self._get_report_from_name(reportname)
        report_obj = request.registry[report.model]
        docs = report_obj.browse(request.cr, request.uid, ids, context=request.context)

        docargs = {
            'doc_ids': ids,
            'doc_model': report.model,
            'docs': docs,
        }

        return request.registry['report'].render(request.cr, request.uid, [], report.report_file,
                                                 docargs, context=request.context)

    def _get_report_from_name(self, report_name):
        """Get the first record of ir.actions.report.xml having the argument as value for
        the field report_name.
        """
        report_obj = request.registry['ir.actions.report.xml']
        qwebtypes = ['qweb-pdf', 'qweb-html']

        idreport = report_obj.search(request.cr, request.uid,
                                     [('report_type', 'in', qwebtypes),
                                      ('report_name', '=', report_name)])

        report = report_obj.browse(request.cr, request.uid, idreport[0],
                                   context=request.context)
        return report
