# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class hr(osv.osv):
    _inherit = 'hr.employee'
    _columns = {
        'website_published': fields.boolean('Available in the website', copy=False),
        'public_info': fields.text('Public Info'),
    }
    _defaults = {
        'website_published': False
    }

    def img(self, cr, uid, ids, field='image_small', context=None):
        return "/website/image/%s/%s/%s" % (self._name, ids[0], field)
