# -*- coding: utf-8 -*-
from tools.translate import _
from osv import fields, osv

class task(osv.osv):
    _name = "project.task"
    _inherit = ["project.task",'pad.common']
    _pad_url = 'description'
    _defaults = {
        _pad_url: lambda self, cr, uid, context: self.pad_generate_url(cr, uid, self._name, context),
    }
