# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv

from odoo.addons.calendar.models.calendar import get_real_ids


class ir_attachment(osv.Model):
    _inherit = "ir.attachment"

    def search(self, cr, uid, args, offset=0, limit=0, order=None, context=None, count=False):
        '''
        convert the search on real ids in the case it was asked on virtual ids, then call super()
        '''
        args = list(args)
        if any([leaf for leaf in args if leaf[0] ==  "res_model" and leaf[2] == 'calendar.event']):
            for index in range(len(args)):
                if args[index][0] == "res_id" and isinstance(args[index][2], basestring):
                    args[index] = (args[index][0], args[index][1], get_real_ids(args[index][2]))
        return super(ir_attachment, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)

    def write(self, cr, uid, ids, vals, context=None):
        '''
        when posting an attachment (new or not), convert the virtual ids in real ids.
        '''
        if isinstance(vals.get('res_id'), basestring):
            vals['res_id'] = get_real_ids(vals.get('res_id'))
        return super(ir_attachment, self).write(cr, uid, ids, vals, context=context)
