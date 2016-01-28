# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com)
# Author : Nicolas Bessi (Camptocamp)

import openerp
from openerp.osv import fields, orm

from webkit_report import WebKitParser

class ir_actions_report_xml(orm.Model):
    _inherit = 'ir.actions.report.xml'
    _columns = {
        'webkit_header': fields.property(
            type='many2one', relation='ir.header_webkit',
            string='Webkit Header', help="The header linked to the report",
            required=True),
        'webkit_debug': fields.boolean('Webkit debug',
            help="Enable the webkit engine debugger"),
        'report_webkit_data': fields.text('Webkit Template',
            help="This template will be used if the main report file is not found"),
        'precise_mode': fields.boolean('Precise Mode',
            help="This mode allow more precise element position as each object"
            " is printed on a separate HTML but memory and disk usage are wider.")
    }

    def _lookup_report(self, cr, name):
        """
        Look up a report definition.
        """
        import operator
        import os
        opj = os.path.join

        # First lookup in the deprecated place, because if the report definition
        # has not been updated, it is more likely the correct definition is there.
        # Only reports with custom parser specified in Python are still there.
        if 'report.' + name in openerp.report.interface.report_int._reports:
            new_report = openerp.report.interface.report_int._reports['report.' + name]
            if not isinstance(new_report, WebKitParser):
                new_report = None
        else:
            cr.execute("SELECT * FROM ir_act_report_xml WHERE report_name=%s and report_type=%s", (name, 'webkit'))
            r = cr.dictfetchone()
            if r:
                if r['parser']:
                    parser = operator.attrgetter(r['parser'])(openerp.addons)
                    kwargs = { 'parser': parser }
                else:
                    kwargs = {}

                new_report = WebKitParser('report.'+r['report_name'],
                    r['model'], opj('addons',r['report_rml'] or '/'),
                    header=r['header'], register=False, **kwargs)
            else:
                new_report = None

        if new_report:
            return new_report
        else:
            return super(ir_actions_report_xml, self)._lookup_report(cr, name)
