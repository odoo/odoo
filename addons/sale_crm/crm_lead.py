from openerp.osv import osv, fields


class crm_lead(osv.Model):
    _inherit = 'crm.lead'

    def _get_sale_amount_total(self, cr, uid, ids, fields, args, context=None):
        res = dict.fromkeys(ids, False)
        sale_rec = self.pool['sale.order'].read_group(cr, uid, [('opportunity_id', 'in', ids), ('state', '!=', 'cancel')], ['opportunity_id', 'amount_total'], ['opportunity_id'], context=context)
        for key, value in dict(map(lambda x: (x['opportunity_id'] and x['opportunity_id'][0], x['amount_total']), sale_rec)).items():
            res[key] = value
        return res

    _columns = {
        'sale_amount_total': fields.function(_get_sale_amount_total, string="Total Amount Of Quotations", type="float")
    }
