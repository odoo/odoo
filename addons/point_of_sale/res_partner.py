
import math

from openerp.osv import osv, fields

import openerp.addons.product.product


class res_users(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'ean13' : fields.char('EAN13', size=13, help="BarCode"),
    }

    def _check_ean(self, cr, uid, ids, context=None):
        return all(
            openerp.addons.product.product.check_ean(user.ean13) == True
            for user in self.browse(cr, uid, ids, context=context)
        )

    _constraints = [
        (_check_ean, "Error: Invalid ean code", ['ean13'],),
    ]

