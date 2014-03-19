# -*- coding: utf-8 -*-
import logging

import openerp
import urllib2

_logger = logging.getLogger(__name__)

class TestReports(openerp.tests.HttpCase):
    def test_reports(self):
        registry, cr, uid = self.registry, self.cr, self.uid
        r_model = registry('ir.actions.report.xml')
        domain = [('report_type','like','qweb')]
        for r in r_model.browse(cr, uid, r_model.search(cr, uid, domain)):
            report_model = registry(r.model)
            report_model_ids = report_model.search(cr, uid, [], limit=10)
            if not report_model_ids:
                _logger.info("no record found skipping report %s", r.report_name)
                continue
            if not r.multi:
                report_model_ids = report_model_ids[:1]
            url = "/report/%s/%s" % (r.report_name, ','.join(str(i) for i in report_model_ids))
            _logger.info("testing report %s", url)
            # TODO sle: uncomment this
            #content = self.url_open(url)

