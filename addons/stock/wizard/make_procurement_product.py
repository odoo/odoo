# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from openerp.osv import fields, osv


class make_procurement(osv.osv_memory):
    _name = 'make.procurement'
    _description = 'Make Procurements'
    
    def onchange_product_id(self, cr, uid, ids, prod_id, context=None):
        product = self.pool.get('product.product').browse(cr, uid, prod_id, context=context)
        return {'value': {
            'uom_id': product.uom_id.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_variant_count': product.product_tmpl_id.product_variant_count
        }}
    
    _columns = {
        'qty': fields.float('Quantity', digits=(16,2), required=True),
        'res_model': fields.char('Res Model'),
        'product_id': fields.many2one('product.product', 'Product', required=True),
        'product_tmpl_id': fields.many2one('product.template', 'Template', required=True),
        'product_variant_count': fields.related('product_tmpl_id', 'product_variant_count', type='integer', string='Variant Number'),
        'uom_id': fields.many2one('product.uom', 'Unit of Measure', required=True),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True),
        'date_planned': fields.date('Planned Date', required=True),
        'route_ids': fields.many2many('stock.location.route', string='Preferred Routes'),
    }

    _defaults = {
        'date_planned': fields.date.context_today,
        'qty': lambda *args: 1.0,
    }

    def make_procurement(self, cr, uid, ids, context=None):
        """ Creates procurement order for selected product. """
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context).login
        wh_obj = self.pool.get('stock.warehouse')
        procurement_obj = self.pool.get('procurement.order')
        data_obj = self.pool.get('ir.model.data')

        for proc in self.browse(cr, uid, ids, context=context):
            wh = wh_obj.browse(cr, uid, proc.warehouse_id.id, context=context)
            procure_id = procurement_obj.create(cr, uid, {
                'name':'INT: '+str(user),
                'date_planned': proc.date_planned,
                'product_id': proc.product_id.id,
                'product_qty': proc.qty,
                'product_uom': proc.uom_id.id,
                'warehouse_id': proc.warehouse_id.id,
                'location_id': wh.lot_stock_id.id,
                'company_id': wh.company_id.id,
                'route_ids': [(6, 0, proc.route_ids.ids)],
            }, context=context)
            procurement_obj.signal_workflow(cr, uid, [procure_id], 'button_confirm')

        id2 = data_obj._get_id(cr, uid, 'procurement', 'procurement_tree_view')
        id3 = data_obj._get_id(cr, uid, 'procurement', 'procurement_form_view')

        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        if id3:
            id3 = data_obj.browse(cr, uid, id3, context=context).res_id

        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'procurement.order',
            'res_id' : procure_id,
            'views': [(id3,'form'),(id2,'tree')],
            'type': 'ir.actions.act_window',
         }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        record_id = context.get('active_id')

        if context.get('active_model') == 'product.template':
            product_ids = self.pool.get('product.product').search(cr, uid, [('product_tmpl_id', '=', context.get('active_id'))], context=context)
            if product_ids:
                record_id = product_ids[0]

        res = super(make_procurement, self).default_get(cr, uid, fields, context=context)

        if record_id and 'product_id' in fields:
            proxy = self.pool.get('product.product')
            product_ids = proxy.search(cr, uid, [('id', '=', record_id)], context=context, limit=1)
            if product_ids:
                product_id = product_ids[0]

                product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
                res['product_id'] = product.id
                res['uom_id'] = product.uom_id.id

        if 'warehouse_id' in fields:
            warehouse_id = self.pool.get('stock.warehouse').search(cr, uid, [], context=context)
            res['warehouse_id'] = warehouse_id[0] if warehouse_id else False

        return res

    def create(self, cr, uid, values, context=None):
        if values.get('product_id'):
            values.update(self.onchange_product_id(cr, uid, None, values['product_id'], context=context)['value'])
        return super(make_procurement, self).create(cr, uid, values, context=context)
