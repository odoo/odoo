#!/usr/bin/env python

from openerp.osv import osv, fields
from openerp.tools import image_resize_image

class Company(osv.Model):
    _inherit = 'res.company'

    def _get_logo_web(self, cr, uid, ids, _field_name, _args, context=None):
        result = dict.fromkeys(ids, False)
        for record in self.browse(cr, uid, ids, context=context):
            size = (180, None)
            result[record.id] = image_resize_image(record.partner_id.image, size)
        return result

    def _get_companies_from_partner(self, cr, uid, ids, context=None):
        return self.pool['res.company'].search(cr, uid, [('partner_id', 'in', ids)], context=context)

    _columns = {
        'logo_web': fields.function(_get_logo_web, string="Logo Web", type="binary", store={
            'res.company': (lambda s, c, u, i, x: i, ['partner_id'], 10),
            'res.partner': (_get_companies_from_partner, ['image'], 10),
        }),
    }
