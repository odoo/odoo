# -*- coding: utf-8 -*-
from tools.translate import _
from osv import fields, osv

class task(osv.osv):
    _name = "project.task"
    _inherit = ["project.task",'pad.common']
    _pad_fields = ['description_pad']
    _columns = {
        'description_pad': fields.char('Description PAD', size=250)
    }
    _defaults = {
        'description_pad': lambda self, cr, uid, context: self.pad_generate_url(cr, uid, context),
    }
