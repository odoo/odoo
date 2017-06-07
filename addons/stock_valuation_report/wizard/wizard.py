from openerp.osv import fields, osv


class wizard_valuation_report(osv.osv_memory):

    _name = 'wizard.valuation.report'
    _description = 'Wizard that opens the stock valuation history table'
    _columns = {
        'date': fields.datetime('Date', required=True),
        'product_category_id': fields.many2one('product.category', 'Category', required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', string="Warehouse"),
        'location_id': fields.many2one('stock.location', string="Location"),
        'method': fields.selection([('internal', 'All Internal Locations'), ('internal_transit', 'All Internal and Transit Locations'),
                                    ('location', 'Specific Location'), ('warehouse', 'Specific Warehouse')],
                                   string="Which Locations?")
    }

    _defaults = {
        'date': fields.datetime.now,
        'company_id': lambda self, cr, uid, c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
        'method': 'internal',
    }

    def print_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        res = self.read(cr, uid, ids, ['date', 'product_category_id', 'company_id', 'method', 'location_id', 'warehouse_id'], context=context)
        res = res and res[0] or {}
        if res.get('id', False):
            datas['ids'] = [res['id']]
        datas['form'] = res
        return self.pool['report'].get_action(cr, uid, [], 'stock_valuation_report.valuation_report', data=datas, context=context)
