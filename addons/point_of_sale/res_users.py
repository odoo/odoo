
from openerp.osv import osv, fields


class res_users(osv.osv):
    _inherit = 'res.users'
    _columns = {
        'pos_security_pin': fields.char('Security PIN',size=32, help='A Security PIN used to protect sensible functionality in the Point of Sale'),
        'pos_config' : fields.many2one('pos.config', 'Default Point of Sale', domain=[('state', '=', 'active')]),
    }

    def _check_pin(self, cr, uid, ids, context=None):
        for user in self.browse(cr, uid, ids, context=context):
            if user.pos_security_pin and not user.pos_security_pin.isdigit():
                return False
        return True

    _constraints = [
        (_check_pin, "Security PIN can only contain digits",['pos_security_pin']),
    ]
