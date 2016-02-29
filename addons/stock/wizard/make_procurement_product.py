# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, fields, models

class MakeProcurement(models.TransientModel):
    _name = 'make.procurement'
    _description = 'Make Procurements'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.uom_id = self.product_id.uom_id
        self.product_tmpl_id = self.product_id.product_tmpl_id
        self.product_variant_count = self.product_id.product_tmpl_id.product_variant_count

    qty = fields.Float('Quantity', digits=(16,2), required=True, default=1.0)
    res_model = fields.Char('Res Model')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_tmpl_id = fields.Many2one('product.template', 'Template', required=True)
    product_variant_count = fields.Integer(related='product_tmpl_id.product_variant_count', string='Variant Number')
    uom_id = fields.Many2one('product.uom', 'Unit of Measure', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    date_planned = fields.Date('Planned Date', required=True, default=fields.Date.context_today)
    route_ids = fields.Many2many('stock.location.route', string='Preferred Routes')

    @api.multi
    def make_procurement(self):
        """ Creates procurement order for selected product. """
        user = self.env.user.login
        ProcurementOrder = self.env['procurement.order']

        for proc in self:
            procurement = ProcurementOrder.create({
                'name':'INT: '+ str(user),
                'date_planned': proc.date_planned,
                'product_id': proc.product_id.id,
                'product_qty': proc.qty,
                'product_uom': proc.uom_id.id,
                'warehouse_id': proc.warehouse_id.id,
                'location_id': proc.warehouse_id.lot_stock_id.id,
                'company_id': proc.warehouse_id.company_id.id,
                'route_ids': [(6, 0, proc.route_ids.ids)],
            })
            procurement.signal_workflow('button_confirm')

        tree_view_id = self.env.ref('procurement.procurement_tree_view').model_data_id.res_id
        form_view_id = self.env.ref('procurement.procurement_form_view').model_data_id.res_id

        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'procurement.order',
            'res_id' : procurement.id,
            'views': [(form_view_id, 'form'), (tree_view_id, 'tree')],
            'type': 'ir.actions.act_window',
         }

    @api.model
    def default_get(self, fields):
        context = dict(self.env.context)
        Product = self.env['product.product']
        record_id = context.get('active_id')

        if context.get('active_model') == 'product.template':
            product = Product.search([('product_tmpl_id', '=', context.get('active_id'))], limit=1)
            record_id = product.id

        res = super(MakeProcurement, self).default_get(fields)

        if record_id and 'product_id' in fields:
            product = Product.search([('id', '=', record_id)], limit=1)
            if product:
                res['product_id'] = product.id
                res['uom_id'] = product.uom_id.id

        if 'warehouse_id' in fields:
            res['warehouse_id'] = self.env['stock.warehouse'].search([], limit=1).id

        return res

    @api.model
    def create(self, values):
        if values.get('product_id'):
            make_procurement = self.new({'product_id': values['product_id']})
            make_procurement._onchange_product_id()
            values.update(make_procurement._convert_to_write(make_procurement._cache))
        return super(MakeProcurement, self).create(values)
