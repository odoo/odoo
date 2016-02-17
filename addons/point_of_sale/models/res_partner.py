
from openerp.osv import osv, fields


class res_users(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'barcode' : fields.char('Barcode', help="BarCode", oldname='ean13'),
    }