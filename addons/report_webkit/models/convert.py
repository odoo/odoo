# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com)
# Author : Nicolas Bessi (Camptocamp)

from openerp.tools import convert

original_xml_import = convert.xml_import

class WebkitXMLImport(original_xml_import):

    # Override of xml import in order to add webkit_header tag in report tag.
    # As discussed with the R&D Team,  the current XML processing API does
    # not offer enough flexibity to do it in a cleaner way.
    # The solution is not meant to be long term solution, but at least
    # allows chaining of several overrides of the _tag_report method,
    # and does not require a copy/paste of the original code.
    def _tag_report(self, cr, rec, data_node=None, mode=None):
        report_id = super(WebkitXMLImport, self)._tag_report(cr, rec, data_node)
        if rec.get('report_type') == 'webkit':
            header = rec.get('webkit_header')
            if header:
                if header in ('False', '0', 'None'):
                    webkit_header_id = False
                else:
                    webkit_header_id = self.id_get(cr, header)
                self.pool.get('ir.actions.report.xml').write(cr, self.uid,
                    report_id, {'webkit_header': webkit_header_id})
        return report_id

convert.xml_import = WebkitXMLImport
