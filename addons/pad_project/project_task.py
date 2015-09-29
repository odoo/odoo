# -*- coding: utf-8 -*-
from openerp.tools.translate import _
from openerp.osv import fields, osv

class task(osv.osv):
    _name = "project.task"
    _inherit = ["project.task",'pad.common']
    _columns = {
        'description_pad': fields.char('Pad URL', pad_content_field='description')
    }
