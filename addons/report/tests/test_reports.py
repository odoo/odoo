# -*- coding: utf-8 -*-

import logging
import openerp


_logger = logging.getLogger(__name__)


@openerp.tests.common.at_install(False)
@openerp.tests.common.post_install(True)
class TestReports(openerp.tests.TransactionCase):
    def test_reports(self):
        return  # commented out until post_install tests are working

        registry, cr, uid = self.registry, self.cr, self.uid
        r_model = registry('ir.actions.report.xml')
        domain = [('report_type', 'like', 'qweb')]
        for r in r_model.browse(cr, uid, r_model.search(cr, uid, domain)):
            report_model = 'report.%s' % r.report_name
            particular_model = registry('ir.model').search(cr, uid, [('model', '=', report_model)])

            # Only test the generic reports here
            if particular_model:
                continue

            _logger.info("testing report %s", r.report_name)
            report_model = registry(r.model)
            report_model_ids = report_model.search(cr, uid, [], limit=10)
            if not report_model_ids:
                _logger.info("no record found skipping report %s", r.report_name)
            if not r.multi:
                report_model_ids = report_model_ids[:1]

            # Test report generation
            registry('report').get_html(cr, uid, report_model_ids, r.report_name)
