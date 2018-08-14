# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from odoo import api, fields, models

class MakeProcurement(models.TransientModel):
    _name = 'make.procurement'
    _description = 'Make Procurements'

    qty = fields.Float('Quantity', default=1.0, digits=(16, 2), required=True)
    res_model = fields.Char('Res Model')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    product_tmpl_id = fields.Many2one('product.template', 'Template', required=True)
    product_variant_count = fields.Integer(string='Variant Number', related='product_tmpl_id.product_variant_count')
    uom_id = fields.Many2one('product.uom', 'Unit of Measure', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    date_planned = fields.Date('Planned Date', default=fields.Date.context_today, required=True)
    route_ids = fields.Many2many('stock.location.route', string='Preferred Routes')

    @api.model
    def default_get(self, fields):
        # TDE FIXME: clean this method, overly complicated (onchange ?)
        res = super(MakeProcurement, self).default_get(fields)

        if self.env.context.get('active_id') and self.env.context.get('active_model') == 'product.template':
            product = self.env['product.product'].search([('product_tmpl_id', '=', self.env.context['active_id'])], limit=1)
        elif self.env.context.get('active_id') and self.env.context.get('active_model') == 'product.product':
            product = self.env['product.product'].browse(self.env.context['active_id'])
        else:
            product = self.env['product.product']
        if 'product_id' in fields and not res.get('product_id') and product:
            res['product_id'] = product.id
        if 'product_tmpl_id' in fields and not res.get('product_tmpl_id') and product:
            res['product_tmpl_id'] = product.product_tmpl_id.id
        if 'uom_id' in fields and not res.get('uom_id') and product:
            res['uom_id'] = product.uom_id.id
        if 'warehouse_id' in fields and not res.get('warehouse_id'):
            res['warehouse_id'] = self.env['stock.warehouse'].search([], limit=1).id
        return res

    def onchange_product_id_dict(self, product_id):
        product = self.env['product.product'].browse(product_id)
        return {
            'uom_id': product.uom_id.id,
            'product_tmpl_id': product.product_tmpl_id.id,
            'product_variant_count': product.product_tmpl_id.product_variant_count
        }

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            for key, value in self.onchange_product_id_dict(self.product_id.id).iteritems():
                setattr(self, key, value)

    @api.model
    def create(self, values):
        if values.get('product_id'):
            values.update(self.onchange_product_id_dict(values['product_id']))
        return super(MakeProcurement, self).create(values)

    @api.multi
    def make_procurement(self):
        """ Creates procurement order for selected product. """
        ProcurementOrder = self.env['procurement.order']
        for wizard in self:
            # we set the time to noon to avoid the date to be changed because of timezone issues
            date = fields.Datetime.from_string(wizard.date_planned)
            date = date + datetime.timedelta(hours=12)
            date = fields.Datetime.to_string(date)

            procurement = ProcurementOrder.create({
                'name': 'INT: %s' % (self.env.user.login),
                'date_planned': date,
                'product_id': wizard.product_id.id,
                'product_qty': wizard.qty,
                'product_uom': wizard.uom_id.id,
                'warehouse_id': wizard.warehouse_id.id,
                'location_id': wizard.warehouse_id.lot_stock_id.id,
                'company_id': wizard.warehouse_id.company_id.id,
                'route_ids': [(6, 0, wizard.route_ids.ids)]})
        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'procurement.order',
            'res_id': procurement.id,
            'views': [(False, 'form'), (False, 'tree')],
            'type': 'ir.actions.act_window',
        }
