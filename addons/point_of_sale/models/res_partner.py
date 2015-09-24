
import math

from openerp.osv import osv, fields

import openerp.addons.product.product


class res_users(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'barcode' : fields.char('Barcode', help="BarCode", oldname='ean13'),
    }

    def create_from_ui(self, cr, uid, partner, context=None):
        """ create or modify a partner from the point of sale ui.
            partner contains the partner's fields. """

        #image is a dataurl, get the data after the comma
        if partner.get('image',False):
            img =  partner['image'].split(',')[1]
            partner['image'] = img

        if partner.get('id',False):  # Modifying existing partner
            partner_id = partner['id']
            del partner['id']
            self.write(cr, uid, [partner_id], partner, context=context)
        else:
            partner_id = self.create(cr, uid, partner, context=context)
        return partner_id
