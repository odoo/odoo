# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class RemovalStrategy(models.Model):
    _name = 'product.removal'
    _description = 'Removal Strategy'

    name = fields.Char('Name', required=True)
    method = fields.Char("Method", required=True, help="FIFO, LIFO...")


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

    def _default_product_id(self):
        if self.env.context.get('active_model') == 'product.template' and self.env.context.get('active_id'):
            product_template = self.env['product.template'].browse(self.env.context.get('active_id'))
            product_template = product_template.exists()
            if product_template.product_variant_count == 1:
                return product_template.product_variant_id
        elif self.env.context.get('active_model') == 'product.product':
            return self.env.context.get('active_id')

    def _domain_category_id(self):
        active_model = self.env.context.get('active_model')
        if active_model in ('product.template', 'product.product') and self.env.context.get('active_id'):
            product = self.env[active_model].browse(self.env.context.get('active_id'))
            product = product.exists()
            if product:
                return [('id', '=', product.categ_id.id)]
        return []

    def _domain_product_id(self):
        domain = "[('type', '!=', 'service'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]"
        if self.env.context.get('active_model') == 'product.template':
            return [('product_tmpl_id', '=', self.env.context.get('active_id'))]
        return domain

    product_id = fields.Many2one(
        'product.product', 'Product', check_company=True,
        default=_default_product_id, domain=_domain_product_id, ondelete='cascade')
    category_id = fields.Many2one('product.category', 'Product Category',
        default=_default_category_id, domain=_domain_category_id, ondelete='cascade')
    location_in_id = fields.Many2one(
        'stock.location', 'When product arrives in', check_company=True,
        domain="[('child_ids', '!=', False), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        default=_default_location_id, required=True, ondelete='cascade')
    location_out_id = fields.Many2one(
        'stock.location', 'Store to', check_company=True,
        domain="[('id', 'child_of', location_in_id), ('id', '!=', location_in_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        ondelete='cascade')
    automatic = fields.Boolean('Automatic', help="Automatically find a putaway location.")
    sequence = fields.Integer('Priority', help="Give to the more specialized category, a higher priority to have them in top of the list.")
    company_id = fields.Many2one(
        'res.company', 'Company', required=True,
        default=lambda s: s.env.company.id, index=True)

    @api.onchange('automatic', 'product_id', 'category_id')
    def _on_change_automatic(self):
        """When automatic is checked, set location_out_id to None, and check if
        the product or product.category is properly setted.
        """
        if self.automatic:
            self.location_out_id = None
            message = False
            if self.product_id and not self.product_id.product_loc_cat_ids:
                    message = _("This putway rule be ignored because there is no location category defined for this product.")
            elif self.category_id and not self.category_id.product_cat_loc_cat_ids:
                    message = _("This putway rule be ignored because there is no location category defined for this product category.")
            if message:
                return {
                    'warning': {
                        'title': _('No location category defined.'),
                        'message': message,
                    }
                }

    @api.onchange('location_in_id')
    def _onchange_location_in(self):
        if self.location_out_id:
            child_location_count = self.env['stock.location'].search_count([
                ('id', '=', self.location_out_id.id),
                ('id', 'child_of', self.location_in_id.id),
                ('id', '!=', self.location_in_id.id),
            ])
            if not child_location_count:
                self.location_out_id = None

    def write(self, vals):
        if 'company_id' in vals:
            for rule in self:
                if rule.company_id.id != vals['company_id']:
                    raise UserError(_("Changing the company of this record is forbidden at this point, you should rather archive it and create a new one."))
        return super(StockPutawayRule, self).write(vals)

    def _get_putaway_location(self, product, quantity):
        self.ensure_one()
        if not self.automatic and self.location_out_id:
            if self.location_out_id._check_can_be_used(product, quantity):
                return self.location_out_id
            return None

        child_locations = self.env['stock.location'].search([('id', 'child_of', self.location_in_id.id), ('id', '!=', self.location_in_id.id)])
        # check previous locations
        previous_locations = product.stock_quant_ids.filtered(lambda q: q.location_id in child_locations).sorted(lambda q: q.in_date).mapped('location_id')
        for location in previous_locations:
            if location._check_can_be_used(product, quantity):
                return location
            child_locations -= location

        location_category = self.env['stock.location.category']
        # check product location category
        if product.product_loc_cat_ids:
            location_category = product.product_loc_cat_ids.location_category_id
        # check product category location category
        elif product.product_category_id.product_cat_loc_cat_ids:
            location_category = product.product_category_id.product_cat_loc_cat_ids.location_category_id
        for location in location_category.location_ids:
            if location in child_locations:
                if location._check_can_be_used(product, quantity):
                    return location
        return None
