# -*- coding: utf-8 -*-

from openerp.osv import osv, fields

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'website_published': fields.boolean('Available in the website'),
        'website_testimonial': fields.text('Recommandation'),
    }

    def img(self, cr, uid, ids, field='image_small', context=None):
        return "/website/image?model=%s&field=%s&id=%s" % (self._name, field, ids[0])
