# -*- coding: utf-8 -*-

from openerp.osv import osv, fields

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'website_published': fields.boolean('Available in the website'),
        'website_description': fields.html('Description for the website'),
        'website_sort_description': fields.text('Sort description for the website'),
    }

    def img(self, cr, uid, ids, field='image_small', context=None):
        return "/website/image?model=%s&field=%s&id=%s" % (self._name, field, ids[0])
