from openerp.osv import osv, fields

class res_partner(osv.Model):
    _inherit = 'res.partner'
    
    def _contracts_count(self, cr, uid, ids, field_name, arg, context=None):
        result = dict.fromkeys(ids, 0)
        for group in self.pool['account.analytic.account'].read_group(cr, uid, [('partner_id', 'in', ids),('type', '=', 'contract'),('state','in',('open','pending'))], ['partner_id'], ['partner_id'], context=context):
            result[group['partner_id'][0]] = group['partner_id_count']
        return result
    
    _columns = {
        'contracts_count': fields.function(_contracts_count, string="Contracts", type='integer'),
    }

