from openerp.osv import fields, osv


class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def _compute_payment_token_count(self, cr, uid, ids, field_names, arg, context=None):
        result = {}
        payment_data = self.pool['payment.token'].read_group(
            cr, uid, [('partner_id', 'in', ids)], ['partner_id'], ['partner_id'], context=context)
        mapped_data = dict([(payment['partner_id'][0], payment['partner_id_count']) for payment in payment_data])
        for partner in self.browse(cr, uid, ids, context=context):
            result[partner.id] = mapped_data.get(partner.id, 0)
        return result

    _columns = {
        'payment_token_ids': fields.one2many('payment.token', 'partner_id', 'Payment Tokens'),
        'payment_token_count': fields.function(_compute_payment_token_count, string='Count Payment Token', type="integer"),
    }
