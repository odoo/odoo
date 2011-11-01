# -*- coding: utf-8 -*-
from tools.translate import _
from osv import fields, osv

class task(osv.osv):
    _inherit = "project.task"

    def pad_get(self, cr, uid, ids, context=None):
        """Get pad action
        """
        url = self.pool.get("ir.attachment").pad_get(cr, uid, self._name, ids[0])
        return {
            'type': 'ir.actions.act_url',
            'url': url
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
