from odoo import api, fields, models


class RepairServiceLine(models.Model):
    _name = 'repair.service.line'
    _description = "Repair Service Line"
    _order = 'sequence, id'
    _inherit = ['product.catalog.line.mixin']

    repair_id = fields.Many2one('repair.order', check_company=True, index='btree_not_null', copy=False, ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', string='Service',
        domain="[('type', '=', 'service'), '|', ('company_id', '=', company_id), ('company_id', '=', False)]",
        check_company=True)
    uom_id = fields.Many2one(
        'uom.uom', 'Unit', domain="[('id', 'in', allowed_uom_ids)]",
        readonly=False, required=True, compute='_compute_uom_id', store=True, copy=True, precompute=True)
    allowed_uom_ids = fields.Many2many('uom.uom', compute='_compute_allowed_uom_ids')
    quantity = fields.Float(
        'Quantity', digits='Product Unit', required=True, default=1.0)
    company_id = fields.Many2one(related='repair_id.company_id')
    sequence = fields.Integer('Sequence', default=0)
    description = fields.Text(string="Description", translate=True)

    @api.depends('product_id')
    def _compute_uom_id(self):
        for line in self:
            line.uom_id = line.product_id.uom_id

    @api.depends('product_id', 'product_id.uom_id')
    def _compute_allowed_uom_ids(self):
        for line in self:
            line.allowed_uom_ids = line.product_id._get_available_uoms()

    def action_add_service_from_repair_catalog(self):
        repair_order = self.env['repair.order'].browse(self.env.context.get('order_id'))
        return repair_order.with_context(child_field='repair_service_line_ids').action_add_from_catalog()

    def _get_quantity_field(self) -> str:
        return "quantity"

    def _get_product_uom_field(self) -> str:
        return "uom_id"
