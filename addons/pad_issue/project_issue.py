# -*- coding: utf-8 -*-
from openerp.tools.translate import _
from openerp.osv import fields, osv

class issue(osv.osv):
    _name = "project.issue"
    _inherit = ["project.issue",'pad.common']
    _columns = {
        'description_pad': fields.char('Pad URL', pad_content_field='description')
    }
