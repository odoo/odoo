# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ProductionLot(models.Model):
    _name = 'stock.production.lot'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Lot/Serial'
    _check_company_auto = True

    name = fields.Char(
        'Lot/Serial Number', default=lambda self: self.env['ir.sequence'].next_by_code('stock.lot.serial'),
        required=True, help="Unique Lot/Serial Number")
    ref = fields.Char('Internal Reference', help="Internal reference number in case it differs from the manufacturer's lot/serial number")
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain=lambda self: self._domain_product_id(), required=True, check_company=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        related='product_id.uom_id', store=True, readonly=False)
    quant_ids = fields.One2many('stock.quant', 'lot_id', 'Quants', readonly=True)
    product_qty = fields.Float('Quantity', compute='_product_qty')
    note = fields.Html(string='Description')
    display_complete = fields.Boolean(compute='_compute_display_complete')
    company_id = fields.Many2one('res.company', 'Company', required=True, store=True, index=True)

    @api.constrains('name', 'product_id', 'company_id')
    def _check_unique_lot(self):
        domain = [('product_id', 'in', self.product_id.ids),
                  ('company_id', 'in', self.company_id.ids),
                  ('name', 'in', self.mapped('name'))]
        fields = ['company_id', 'product_id', 'name']
        groupby = ['company_id', 'product_id', 'name']
        records = self.read_group(domain, fields, groupby, lazy=False)
        error_message_lines = []
        for rec in records:
            if rec['__count'] != 1:
                product_name = self.env['product.product'].browse(rec['product_id'][0]).display_name
                error_message_lines.append(_(" - Product: %s, Serial Number: %s", product_name, rec['name']))
        if error_message_lines:
            raise ValidationError(_('The combination of serial number and product must be unique across a company.\nFollowing combination contains duplicates:\n') + '\n'.join(error_message_lines))

    def _domain_product_id(self):
        domain = [
            "('tracking', '!=', 'none')",
            "('type', '=', 'product')",
            "'|'",
                "('company_id', '=', False)",
                "('company_id', '=', company_id)"
        ]
        if self.env.context.get('default_product_tmpl_id'):
            domain.insert(0,
                ("('product_tmpl_id', '=', %s)" % self.env.context['default_product_tmpl_id'])
            )
        return '[' + ', '.join(domain) + ']'

    def _check_create(self):
        active_picking_id = self.env.context.get('active_picking_id', False)
        if active_picking_id:
            picking_id = self.env['stock.picking'].browse(active_picking_id)
            if picking_id and not picking_id.picking_type_id.use_create_lots:
                raise UserError(_('You are not allowed to create a lot or serial number with this operation type. To change this, go on the operation type and tick the box "Create New Lots/Serial Numbers".'))

    @api.depends('name')
    def _compute_display_complete(self):
        """ Defines if we want to display all fields in the stock.production.lot form view.
        It will if the record exists (`id` set) or if we precised it into the context.
        This compute depends on field `name` because as it has always a default value, it'll be
        always triggered.
        """
        for prod_lot in self:
            prod_lot.display_complete = prod_lot.id or self._context.get('display_complete')

    @api.model_create_multi
    def create(self, vals_list):
        self._check_create()
        return super(ProductionLot, self).create(vals_list)

    def write(self, vals):
        if 'company_id' in vals:
            for lot in self:
                if lot.company_id.id != vals['company_id']:
                    raise UserError(_("Changing the company of this record is forbidden at this point, you should rather archive it and create a new one."))
        if 'product_id' in vals and any(vals['product_id'] != lot.product_id.id for lot in self):
            move_lines = self.env['stock.move.line'].search([('lot_id', 'in', self.ids), ('product_id', '!=', vals['product_id'])])
            if move_lines:
                raise UserError(_(
                    'You are not allowed to change the product linked to a serial or lot number '
                    'if some stock moves have already been created with that number. '
                    'This would lead to inconsistencies in your stock.'
                ))
        return super(ProductionLot, self).write(vals)

    @api.depends('quant_ids', 'quant_ids.quantity')
    def _product_qty(self):
        for lot in self:
            # We only care for the quants in internal or transit locations.
            quants = lot.quant_ids.filtered(lambda q: q.location_id.usage == 'internal' or (q.location_id.usage == 'transit' and q.location_id.company_id))
            lot.product_qty = sum(quants.mapped('quantity'))

    def action_lot_open_quants(self):
        self = self.with_context(search_default_lot_id=self.id, create=False)
        if self.user_has_groups('stock.group_stock_manager'):
            self = self.with_context(inventory_mode=True)
        return self.env['stock.quant']._get_quants_action()
