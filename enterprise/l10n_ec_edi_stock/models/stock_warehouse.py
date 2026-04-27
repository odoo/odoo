from odoo import fields, models, api, Command, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    l10n_ec_entity = fields.Char(
        string="Entity Point",
        size=3,
        copy=False,
        help="Ecuador: Emission entity number that is given by the SRI."
    )
    l10n_ec_emission = fields.Char(
        string="Emission Point",
        size=3, copy=False,
        help="Ecuador: Emission point number that is given by the SRI."
    )
    l10n_ec_delivery_number = fields.Integer(
        string="Next Delivery Guide Number",
        copy=False,
        readonly=False,
        default=1,
        related='l10n_ec_delivery_number_sequence_id.number_next',
        help="Ecuador: Hold the next sequence to use as delivery guide number.",
    )
    l10n_ec_delivery_number_sequence_id = fields.Many2one(
        comodel_name='ir.sequence',
        string="Delivery Guide Number Sequence",
        help="Ecuador: Hold the sequence to generate a delivery guide number.",
    )
    l10n_ec_country_code = fields.Char(
        string="Country Code(EC)",
        related='company_id.country_code',
        depends=['company_id']
    )

    _sql_constraints = [(
        'unique_warehouse_ec_entity_and_emission', 'UNIQUE(l10n_ec_entity, l10n_ec_emission, company_id)',
        'Duplicated warehouse (entity, emission) pair. You probably encoded twice the same warehouse.'
    )]

    def _l10n_ec_create_delivery_guide_sequence(self):
        """
        Generate the delivery guide number for the warehouse.
        """
        warehouses = self.env['stock.warehouse']
        for warehouse in self:
            if (
                    warehouse.l10n_ec_entity
                    and warehouse.l10n_ec_emission
                    and not warehouse.l10n_ec_delivery_number_sequence_id
            ):
                warehouse.l10n_ec_delivery_number_sequence_id = self.env['ir.sequence'].sudo().create({
                    'name': _('%(company)s - Stock Picking Delivery Guide Sequence for %(entity)s-%(emission)s',
                              company=warehouse.company_id.name,
                              entity=warehouse.l10n_ec_entity,
                              emission=warehouse.l10n_ec_emission,
                              ),
                    'code': f"l10n_ec_edi_stock.stock_picking_dgs_{warehouse.company_id.id}_{warehouse.l10n_ec_entity}_{warehouse.l10n_ec_emission}",
                    'company_id': warehouse.company_id.id,
                    'padding': 9,
                    'implementation': 'no_gap',
                })
                warehouses |= warehouse
        return warehouses

    @api.model_create_multi
    def create(self, vals_list):
        """
        Extends for creating or updating the sequence for the delivery guide number.
        """
        # actually create WH
        warehouses = super().create(vals_list)
        warehouses._l10n_ec_create_delivery_guide_sequence()
        return warehouses

    def write(self, vals):
        """
        Extends for updating the sequence for the delivery guide number when the entity or emission changes.
        """
        res = super().write(vals)
        warehouses = self - self._l10n_ec_create_delivery_guide_sequence()
        for warehouse in warehouses:
            if ('l10n_ec_entity' in vals or 'l10n_ec_emission' in vals) and warehouse.l10n_ec_delivery_number_sequence_id:
                warehouse.sudo().l10n_ec_delivery_number_sequence_id.write({
                    'name': _('%(company)s - Stock Picking Delivery Guide Sequence for %(entity)s-%(emission)s',
                              company=warehouse.company_id.name,
                              entity=warehouse.l10n_ec_entity,
                              emission=warehouse.l10n_ec_emission,
                              ),
                    'code': f"l10n_ec_edi_stock.stock_picking_dgs_{warehouse.company_id.id}_{warehouse.l10n_ec_entity}_{warehouse.l10n_ec_emission}",
                    'company_id': warehouse.company_id.id,
                })
        return res