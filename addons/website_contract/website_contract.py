# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class hr(osv.osv):
    _inherit = 'res.partner'
    def img(self, cr, uid, ids, field='image_small', context=None):
        return "/website/image?model=%s&field=%s&id=%s" % (self._name, field, ids[0])
