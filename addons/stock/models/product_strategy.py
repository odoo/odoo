# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.osv import expression
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class RemovalStrategy(models.Model):
    _name = 'product.removal'
    _description = 'Removal Strategy'

    name = fields.Char('Name', required=True, translate=True)
    method = fields.Char("Method", required=True, translate=True, help="FIFO, LIFO...")


class StockPutawayRule(models.Model):
    _name = 'stock.putaway.rule'
    _order = 'sequence,product_id'
    _description = 'Putaway Rule'
    _check_company_auto = True

    def _default_category_id(self):
        if self.env.context.get('active_model') == 'product.category':
            return self.env.context.get('active_id')

    def _default_location_id(self):
        if self.env.context.get('active_model') == 'stock.location':
            return self.env.context.get('active_id')
        if not self.env.user.has_group('stock.group_stock_multi_warehouses'):
            wh = self.env['stock.warehouse'].search(self.env['stock.warehouse']._check_company_domain(self.env.company), limit=1)
            input_loc, _ = wh._get_input_output_locations(wh.reception_steps, wh.delivery_steps)
            return input_loc

    def _default_product_id(self):
        if self.env.context.get('active_model') == 'product.template' and self.env.context.get('active_id'):
            product_template = self.env['product.template'].browse(self.env.context.get('active_id'))
            product_template = product_template.exists()
            if product_template.product_variant_count == 1:
                return product_template.product_variant_id
        elif self.env.context.get('active_model') == 'product.product':
            return self.env.context.get('active_id')

    product_id = fields.Many2one(
        'product.product', 'Product', check_company=True,
        default=_default_product_id,
        domain="[('product_tmpl_id', '=', context.get('active_id', False))] if context.get('active_model') == 'product.template' else [('type', '!=', 'service')]",
        ondelete='cascade')
    category_id = fields.Many2one('product.category', 'Product Category',
        default=_default_category_id, domain=[('filter_for_stock_putaway_rule', '=', True)], ondelete='cascade')
    location_in_id = fields.Many2one(
        'stock.location', 'When product arrives in', check_company=True,
        domain="[('child_ids', '!=', False)]",
        default=_default_location_id, required=True, ondelete='cascade', index=True)
    location_out_id = fields.Many2one(
        'stock.location', 'Store to sublocation', check_company=True,
        domain="[('id', 'child_of', location_in_id)]",
        required=True, ondelete='cascade')
    sequence = fields.Integer('Priority', help="Give to the more specialized category, a higher priority to have them in top of the list.")
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda s: s.env.company.id, index=True)
    package_type_ids = fields.Many2many('stock.package.type', string='Package Type', check_company=True)
    storage_category_id = fields.Many2one(
        'stock.storage.category', 'Storage Category',
        compute='_compute_storage_category', store=True, readonly=False,
        ondelete='cascade', check_company=True)
    active = fields.Boolean('Active', default=True)
    sublocation = fields.Selection([
        ('no', 'No'),
        ('last_used', 'Last Used'),
        ('closest_location', 'Closest Location')
    ], default='no')

    @api.depends('sublocation')
    def _compute_storage_category(self):
        for rule in self:
            if rule.sublocation != 'closest_location':
                rule.storage_category_id = False

    @api.onchange('sublocation', 'location_out_id', 'storage_category_id')
    def _onchange_sublocation(self):
        if self.sublocation == 'closest_location':
            child_location_ids = self.env['stock.location'].search([
                ('id', 'child_of', self.location_out_id.id),
                ('storage_category_id', '=', self.storage_category_id.id)
            ])
            if not child_location_ids:
                return {
                    'warning': {
                        'title': _("Warning"),
                        'message': _("Selected storage category does not exist in the 'store to' location or any of its sublocations"),
                    },
                }

    @api.onchange('location_in_id')
    def _onchange_location_in(self):
        child_location_count = 0
        if self.location_out_id:
            child_location_count = self.env['stock.location'].search_count([
                ('id', '=', self.location_out_id.id),
                ('id', 'child_of', self.location_in_id.id),
                ('id', '!=', self.location_in_id.id),
            ])
        if not child_location_count or not self.location_out_id:
            self.location_out_id = self.location_in_id

    @api.model_create_multi
    def create(self, vals_list):
        rules = super().create(vals_list)
        return rules

    def write(self, vals):
        if 'company_id' in vals:
            for rule in self:
                if rule.company_id.id != vals['company_id']:
                    raise UserError(_("Changing the company of this record is forbidden at this point, you should rather archive it and create a new one."))
        return super(StockPutawayRule, self).write(vals)

    def _get_last_used_search_domain(self, product):
        self.ensure_one()
        domain = expression.AND([
            [('state', '=', 'done')],
            [('location_dest_id', 'child_of', self.location_out_id.id)],
            [('product_id', '=', product.id)],
        ])
        if self.package_type_ids:
            domain = expression.AND([
                domain,
                [('result_package_id.package_type_id', 'in', self.package_type_ids.ids)],
            ])
        return domain

    def _get_last_used_location(self, product):
        self.ensure_one()
        return self.env['stock.move.line'].search(
            domain=self._get_last_used_search_domain(product),
            limit=1,
            order='date desc'
        ).location_dest_id

    def _get_putaway_location(self, product, quantity=0, package=None, packaging=None, qty_by_location=None):
        # find package type on package or packaging
        package_type = self.env['stock.package.type']
        if package:
            package_type = package.package_type_id
        elif packaging:
            package_type = packaging.package_type_id

        checked_locations = set()
        for putaway_rule in self:
            location_out = putaway_rule.location_out_id
            if putaway_rule.sublocation == 'last_used':
                location_dest_id = putaway_rule._get_last_used_location(product)
                location_out = location_dest_id or location_out

            child_locations = location_out.child_internal_location_ids

            if not putaway_rule.storage_category_id:
                if location_out in checked_locations:
                    continue
                if location_out._check_can_be_used(product, quantity, package, qty_by_location[location_out.id]):
                    return location_out
                continue
            else:
                child_locations = child_locations.filtered(lambda loc: loc.storage_category_id == putaway_rule.storage_category_id)

            # check if already have the product/package type stored
            for location in child_locations:
                if location in checked_locations:
                    continue
                if package_type:
                    if location.quant_ids.filtered(lambda q: q.package_id and q.package_id.package_type_id == package_type):
                        if location._check_can_be_used(product, quantity, package=package, location_qty=qty_by_location[location.id]):
                            return location
                        else:
                            checked_locations.add(location)
                elif float_compare(qty_by_location[location.id], 0, precision_rounding=product.uom_id.rounding) > 0:
                    if location._check_can_be_used(product, quantity, location_qty=qty_by_location[location.id]):
                        return location
                    else:
                        checked_locations.add(location)

            # check locations with matched storage category
            for location in child_locations.filtered(lambda l: l.storage_category_id == putaway_rule.storage_category_id):
                if location in checked_locations:
                    continue
                if location._check_can_be_used(product, quantity, package, qty_by_location[location.id]):
                    return location
                checked_locations.add(location)

        return None
