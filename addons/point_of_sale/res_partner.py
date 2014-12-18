
import math

from openerp.osv import osv, fields

import openerp.addons.product.product


class res_users(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'barcode' : fields.char('Barcode', help="BarCode", oldname='ean13'),
    }