# -*- coding: utf-8 -*-

from openerp.osv import osv, fields

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'website_description': fields.html('Description for the website'),
        'website_short_description': fields.text('Sort description for the website'),
    }

    def img(self, cr, uid, ids, field='image_small', context=None):
        return "/website/image?model=%s&field=%s&id=%s" % (self._name, field, ids[0])


class res_partner_grade(osv.osv):
    _inherit = 'res.partner.grade'
    _columns = {
        'website_description': fields.html('Description for the website'),
    }