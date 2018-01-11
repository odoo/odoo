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
import logging

import openerp
import openerp.tests


_logger = logging.getLogger(__name__)


@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestReports(openerp.tests.TransactionCase):
    def test_reports(self):
        registry, cr, uid = self.registry, self.cr, self.uid
        r_model = registry('ir.actions.report.xml')
        domain = [('report_type', 'like', 'qweb')]
        for r in r_model.browse(cr, uid, r_model.search(cr, uid, domain)):
            report_model = 'report.%s' % r.report_name
            try:
                registry(report_model)
            except KeyError:
            # Only test the generic reports here
                _logger.info("testing report %s", r.report_name)
                report_model = registry(r.model)
                report_model_ids = report_model.search(cr, uid, [], limit=10)
                if not report_model_ids:
                    _logger.info("no record found skipping report %s", r.report_name)
                if not r.multi:
                    report_model_ids = report_model_ids[:1]

                # Test report generation
                registry('report').get_html(cr, uid, report_model_ids, r.report_name)
            else:
                continue
