# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv

class report_xml(osv.osv):
    _inherit = 'ir.actions.report.xml'
    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        if context is None:
            context = {}
        object_id = context.get('object_id')
        if object_id:
            model = self.pool.get('ir.model').browse(cr, uid, object_id, context=context).model
            args.append(('model', '=', model))
        return super(report_xml, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)
