from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _default_warehouse_id(self):
        return self.env['stock.warehouse'].search(self.env['stock.warehouse']._check_company_domain(self.env.company), limit=1).id

    def _default_picking_type_id(self):
        warehouse = self.env['stock.warehouse'].search(self.env['stock.warehouse']._check_company_domain(self.env.company), limit=1)
        if not warehouse.pos_type_id:
            warehouse._create_missing_pos_picking_types()
        return warehouse.pos_type_id.id

    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Operation Type',
        default=_default_picking_type_id,
        required=True,
        domain=lambda self: [('code', '=', 'outgoing'), ('warehouse_id.company_id', '=', self.env.company.id)],
        ondelete='restrict')
    ship_later = fields.Boolean(string="Ship Later")
    warehouse_id = fields.Many2one('stock.warehouse', default=_default_warehouse_id, ondelete='restrict')
    route_id = fields.Many2one('stock.route', string="Specific route for products delivered later.")
    picking_policy = fields.Selection([
        ('direct', 'As soon as possible, with back orders'),
        ('one', 'When all products are ready')],
        string='Shipping Policy', required=True, default='direct',
        help="If you deliver all products at once, the delivery order will be scheduled based on the greatest "
        "product lead time. Otherwise, it will be based on the shortest.")

    @api.model_create_multi
    def create(self, vals_list):
        if not self._default_warehouse_id():
            self.env['stock.warehouse'].create({
                'code': vals_list[0].get('name')[:3],  # first 3 characters of pos.config name
                'company_id': self.env.company.id,
            })

        return super().create(vals_list)
