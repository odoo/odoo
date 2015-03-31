from openerp.osv import fields, osv


class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'
    _columns = {
        'payment_method_ids': fields.one2many('payment.method', 'partner_id', 'Payment Methods'),
    }
