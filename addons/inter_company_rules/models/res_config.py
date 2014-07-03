
from openerp.osv import osv, fields

class inter_company_rules_configuration(osv.TransientModel):
    _inherit = 'base.config.settings'

    _columns = {
        'company_id': fields.many2one('res.company', string="Select Company", help="Select company to setup Inter company rules."),
        'set_type': fields.selection([('so_and_po', 'SO and PO setting for inter company'), ('invoice_and_refunds', 'Create Invoice/Refunds when encoding invoice/refunds')], help="Select the type to setup inter company rules in selected company."),
        'so_from_po': fields.boolean("Create Sale Orders when buying to this company", help='Generate a Sale Order when a Purchase Order with this company as supplier is created.'),
        'po_from_so': fields.boolean("Create Purchase Orders when selling to this company", help='Generate a Purchase Order when a Sale Order with this company as customer is created.'),
        'auto_validation': fields.boolean('Sale/Purchase Orders Auto Validation', help="When a Sale Order or a Purchase Order is created by a multi company rule for this company, it will automatically validate it."),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse For Purchase Orders', help="Default value to set on Purchase Orders that will be created based on Sale Orders made to this company.")
    }

    _defaults= {
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'base.config.settings', context=c),
    }

    def onchange_set_type(self, cr, uid, ids, set_type, context=None):
        values = {}
        if set_type == 'invoice_and_refunds':
            values.update({
                'so_from_po': False,
                'po_from_so': False,
                'auto_validation' : False
            })
        elif set_type == 'so_and_po':
            values['invoice_and_refunds'] = False
        return {'value': values}

    def onchange_company_id(self, cr, uid, ids, company_id, context=None):
        values = {}
        if company_id:
            company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
            set_type = False
            if company.so_from_po or company.po_from_so or company.auto_validation:
                set_type = 'so_and_po'
            elif company.auto_generate_invoices:
                set_type = 'invoice_and_refunds'
            values.update({
                'set_type': set_type,
                'so_from_po': company.so_from_po,
                'po_from_so': company.po_from_so,
                'auto_validation': company.auto_validation,
                'warehouse_id': company.warehouse_id.id,
            })
        return {'value': values}

    def set_inter_company_configuration(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context=context)
        if config.company_id:
            vals = {
                'so_from_po': config.so_from_po,
                'po_from_so': config.po_from_so,
                'auto_validation': config.auto_validation,
                'auto_generate_invoices': True if config.set_type == 'invoice_and_refunds' else False,
                'warehouse_id': config.warehouse_id.id
            }
            self.pool.get('res.company').write(cr, uid, [config.company_id.id], vals, context=context)
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
