from odoo import api, models, fields
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context
from odoo.tools import float_compare


class ProductScrap(models.TransientModel):
    _name = 'product.scrap'
    _description = 'Product Scrap'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)
    origin = fields.Char(string='Source Document')
    product_id = fields.Many2one('product.product', 'Product', required=True, check_company=True)
    allowed_uom_ids = fields.Many2many('uom.uom', compute='_compute_allowed_uom_ids')
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit', domain="[('id', 'in', allowed_uom_ids)]",
        compute="_compute_product_uom_id", store=True, readonly=False, precompute=True,
        required=True)
    tracking = fields.Selection(string='Product Tracking', readonly=True, related="product_id.tracking")
    lot_id = fields.Many2one(
        'stock.lot', 'Lot/Serial', check_company=True)
    package_id = fields.Many2one(
        'stock.quant.package', 'Package',
        check_company=True)
    owner_id = fields.Many2one('res.partner', 'Owner', check_company=True)
    picking_id = fields.Many2one('stock.picking', 'Picking', check_company=True)
    location_id = fields.Many2one(
        'stock.location', 'Source Location',
        compute='_compute_location_id', store=True, required=True, precompute=True,
        domain="[('usage', '=', 'internal')]", check_company=True, readonly=False)
    scrap_location_id = fields.Many2one(
        'stock.location', 'Scrap Location',
        compute='_compute_scrap_location_id', store=True, required=True, precompute=True,
        domain="[('scrap_location', '=', True)]", check_company=True, readonly=False)
    scrap_qty = fields.Float('Quantity', required=True, digits='Product Unit', default=1.0, readonly=False, store=True)
    should_replenish = fields.Boolean(string='Replenish Quantities', help="Trigger replenishment for scrapped products")
    scrap_reason_tag_ids = fields.Many2many(
        comodel_name='stock.scrap.reason.tag',
        string='Scrap Reason',
    )

    @api.depends('product_id', 'product_id.uom_id', 'product_id.uom_ids', 'product_id.seller_ids', 'product_id.seller_ids.product_uom_id')
    def _compute_allowed_uom_ids(self):
        for wizard in self:
            wizard.allowed_uom_ids = wizard.product_id.uom_id | wizard.product_id.uom_ids | wizard.product_id.seller_ids.product_uom_id

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for wizard in self:
            wizard.product_uom_id = wizard.product_id.uom_id

    @api.depends('company_id', 'picking_id')
    def _compute_location_id(self):
        company_warehouses = self.env['stock.warehouse'].search([('company_id', 'in', self.company_id.ids)])
        if len(company_warehouses) == 0 and self.company_id:
            self.env['stock.warehouse']._warehouse_redirect_warning()
        groups = company_warehouses._read_group(
            [('company_id', 'in', self.company_id.ids)], ['company_id'], ['lot_stock_id:array_agg'])
        locations_per_company = {
            company.id: lot_stock_ids[0] if lot_stock_ids else False
            for company, lot_stock_ids in groups
        }
        for wizard in self:
            if wizard.picking_id:
                wizard.location_id = wizard.picking_id.location_dest_id if wizard.picking_id.state == 'done' else wizard.picking_id.location_id
            elif wizard.company_id:
                wizard.location_id = locations_per_company[wizard.company_id.id]

    @api.depends('company_id')
    def _compute_scrap_location_id(self):
        groups = self.env['stock.location']._read_group(
            [('company_id', 'in', self.company_id.ids), ('scrap_location', '=', True)], ['company_id'], ['id:min'])
        locations_per_company = {
            company.id: stock_warehouse_id
            for company, stock_warehouse_id in groups
        }
        for wizard in self:
            if wizard.company_id:
                wizard.scrap_location_id = locations_per_company[wizard.company_id.id]

    @api.onchange('lot_id')
    def _onchange_serial_number(self):
        if self.product_id.tracking == 'serial' and self.lot_id:
            message, recommended_location = self.env['stock.quant'].sudo()._check_serial_number(self.product_id,
                                                                                                self.lot_id,
                                                                                                self.company_id,
                                                                                                self.location_id,
                                                                                                self.picking_id.location_dest_id)
            if message:
                if recommended_location:
                    self.location_id = recommended_location
                return {'warning': {'title': self.env._('Warning'), 'message': message}}

    def _prepare_move_values(self):
        self.ensure_one()
        return {
            'origin': self.origin or self.picking_id.name or self.name,
            'company_id': self.company_id.id,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'state': 'draft',
            'product_uom_qty': self.scrap_qty,
            'location_id': self.location_id.id,
            'scrapped': True,
            'location_dest_id': self.scrap_location_id.id,
            'move_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'product_uom_id': self.product_uom_id.id,
                'quantity': self.scrap_qty,
                'location_id': self.location_id.id,
                'location_dest_id': self.scrap_location_id.id,
                'package_id': self.package_id.id,
                'owner_id': self.owner_id.id,
                'lot_id': self.lot_id.id,
            })],
            # 'restrict_partner_id': self.owner_id.id,
            'picked': True,
            'picking_id': self.picking_id.id
        }

    def do_scrap(self):
        self._check_company()
        for wizard in self:
            move = self.env['stock.move'].create(wizard._prepare_move_values())
            # master: replace context by cancel_backorder
            move.with_context(is_scrap=True)._action_done()
            if wizard.should_replenish:
                wizard.do_replenish()
        return True

    def do_replenish(self, values=False):
        self.ensure_one()
        values = values or {}
        self.with_context(clean_context(self.env.context)).env['procurement.group'].run([self.env['procurement.group'].Procurement(
            self.product_id,
            self.scrap_qty,
            self.product_uom_id,
            self.location_id,
            self.name,
            self.name,
            self.company_id,
            values
        )])

    def _should_check_available_qty(self):
        return self.product_id.is_storable

    def check_available_qty(self):
        if not self._should_check_available_qty():
            return True

        precision = self.env['decimal.precision'].precision_get('Product Unit')
        available_qty = self.with_context(
            location=self.location_id.id,
            lot_id=self.lot_id.id,
            package_id=self.package_id.id,
            owner_id=self.owner_id.id,
            strict=True,
        ).product_id.qty_available
        scrap_qty = self.product_uom_id._compute_quantity(self.scrap_qty, self.product_id.uom_id)
        return float_compare(available_qty, scrap_qty, precision_digits=precision) >= 0

    def action_validate(self):
        self.ensure_one()
        if self.product_uom_id.is_zero(self.scrap_qty):
            raise UserError(self.env._('You can only enter positive quantities.'))
        if self.check_available_qty():
            return self.do_scrap()
        else:
            ctx = dict(self.env.context)
            ctx.update({
                'default_product_id': self.product_id.id,
                'default_location_id': self.location_id.id,
                'default_scrap_id': self.id,
                'default_quantity': self.product_uom_id._compute_quantity(self.scrap_qty, self.product_id.uom_id),
                'default_product_uom_name': self.product_id.uom_name
            })
            return {
                'name': self.env._('%(product)s: Insufficient Quantity To Scrap', product=self.product_id.display_name),
                'view_mode': 'form',
                'res_model': 'stock.warn.insufficient.qty.scrap',
                'view_id': self.env.ref('stock.stock_warn_insufficient_qty_scrap_form_view').id,
                'type': 'ir.actions.act_window',
                'context': ctx,
                'target': 'new'
            }
