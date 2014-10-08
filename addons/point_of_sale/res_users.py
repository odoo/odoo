
import math

from openerp.osv import osv, fields

import openerp.addons.product.product


class res_users(osv.osv):
    _inherit = 'res.users'
    _columns = {
        'barcode' : fields.char('Barcode', help="BarCode", oldname='ean13'),
        'pos_security_pin': fields.char('Security PIN',size=32, help='A Security PIN used to protect sensible functionality in the Point of Sale'),
        'pos_config' : fields.many2one('pos.config', 'Default Point of Sale', domain=[('state', '=', 'active')]),
    }

