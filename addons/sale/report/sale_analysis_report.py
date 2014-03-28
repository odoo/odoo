 # -*- coding: utf-8 -*-

from openerp.osv import fields, osv


class sale_report(osv.osv):
    _inherit = "sale.report"
    _columns = {
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
    }

    def _select(self):
        return super(sale_report, self)._select() + ", s.section_id as section_id"

    def _group_by(self):
        return super(sale_report, self)._group_by() + ", s.section_id"

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
