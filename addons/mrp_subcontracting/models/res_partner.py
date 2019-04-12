# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    type = fields.Selection(selection_add=[('subcontractor', 'Subcontractor')])
    bom_id = fields.Many2one('mrp.bom', domain=[('type', '=', 'subcontract')])

    def _get_name(self):
        name = super(ResPartner, self)._get_name()
        if self.type == 'subcontractor':
            subcontractor = _('Subcontractor')
            if name.endswith(', '):
                name = "%s%s" % (name, subcontractor)
            else:
                name = '%s, %s' % (name, subcontractor)
        return name

    @api.onchange('type')
    def _onchange_partner_type(self):
        if self.type == 'subcontractor':
            company = self.company_id or self.parent_id.company_id
            subcontracting_location = company.subcontracting_location_id
            self.update({
                'property_stock_customer': subcontracting_location,
                'property_stock_supplier': subcontracting_location
            })
        else:
            self.update({
                'property_stock_customer': self.env.ref('stock.stock_location_customers'),
                'property_stock_supplier': self.env.ref('stock.stock_location_suppliers')
            })

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('type') == 'subcontractor':
                if not vals.get('property_stock_supplier') and not vals.get('property_stock_customer'):
                    company = vals.get('company_id') and self.env['res.company'].browse(vals['company_id']) or \
                              self.browse(vals.get('parent_id')).company_id
                    subcontracting_location = company.subcontracting_location_id
                    vals['property_stock_supplier'] = subcontracting_location
                    vals['property_stock_customer'] = subcontracting_location
        return super(ResPartner, self).create(vals_list)

    def write(self, vals):
        if vals.get('type') == 'subcontractor':
            subcontracting_location = self.env.user.company_id.subcontracting_location_id
            if not vals.get('property_stock_supplier') and not vals.get('property_stock_customer'):
                vals['property_stock_supplier'] = subcontracting_location.id
                vals['property_stock_customer'] = subcontracting_location.id
        return super(ResPartner, self).write(vals)
