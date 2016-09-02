# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.report import report_sxw

class rmlparser(report_sxw.rml_parse):
    def set_context(self, objects, data, ids, report_type = None):
        super(rmlparser,self).set_context(objects, data, ids, report_type)
        self.setCompany(objects[0])

report_sxw.report_sxw('report.preview.report', 'res.company',
      'addons/base/report/preview_report.rml', parser=rmlparser, header='external')
