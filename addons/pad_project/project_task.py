# -*- coding: utf-8 -*-
from openerp.tools.translate import _
from openerp.osv import fields, osv

class task(osv.osv):
    _name = "project.task"
    _inherit = ["project.task",'pad.common']
    _columns = {
        'description_pad': fields.char('Pad URL', pad_content_field='description')
    }

    def create(self, cr, uid, vals, context=None):
        res = super(task, self).create(cr, uid, vals, context=context)
        # In case the task is created programmatically, 'description_pad' is not filled in yet since
        # it is normally initialized by the JS layer
        if 'description_pad' not in vals:
            ctx = dict(context or {})
            ctx.update({
                'model': 'project.task',
                'field_name': 'description_pad',
                'object_id': res,
            })
            description_pad = self.pad_generate_url(cr, uid, context=ctx)['url']
            self.write(cr, uid, res, {'description_pad': description_pad}, context=context)
        return res
