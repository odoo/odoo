from odoo import api, models, fields


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id'])
    l10n_ro_stock_movement_type = fields.Selection([
            ('10', "Purchase"),
            ('20', "Production"),
            ('30', "Sale of stock"),
            ('40', "Return of sales"),
            ('50', "Return of purchase"),
            ('60', "Discounts received"),
            ('70', "Consumption"),
            ('80', "Internal Transfer"),
            ('90', "Subsequent costs capitalized in the value of the goods"),
            ('100', "Positive price difference"),
            ('101', "Negative price difference"),
            ('110', "Inventory count positive adjustment"),
            ('120', "Inventory count negative adjustment"),
            ('130', "Impairment adjustments for goods"),
            ('140', "Reversal of impairment adjustments for goods"),
            ('150', "Goods granted free of charge"),
            ('160', "Damaged goods"),
            ('170', "Expired goods"),
            ('180', "Other transactions"),
        ],
        string="Movement type (RO)",
        compute='_compute_l10n_ro_stock_movement_type',
        precompute=True,
        store=True,
        readonly=False,
    )

    @api.depends('code')
    def _compute_l10n_ro_stock_movement_type(self):
        for picking_type in self:
            if picking_type.country_code == 'RO' and picking_type.l10n_ro_stock_movement_type in [False, '10', '20', '30', '70', '80']:
                picking_type.l10n_ro_stock_movement_type = {
                    'incoming': '10',
                    'mrp_operation': '20',
                    'outgoing': '30',
                    'repair_operation': '70',
                    'internal': '80',
                }.get(picking_type.code, False)
