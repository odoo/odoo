from odoo import api, models, fields, _
from odoo.exceptions import UserError

from odoo.addons.l10n_pt_stock.models.stock_picking import AT_SERIES_TYPE_MOVEMENT_TYPE_MAP


class L10nPtStockATSeries(models.Model):
    _inherit = "l10n_pt.at.series"

    type = fields.Selection(
        selection_add=[
            ('outgoing_gt', 'Transport Guide (GT)'),
            ('internal_ga', 'Internal Transport Document (GA)'),
            ('incoming_gd', 'Return Note (GD)'),
        ],
        ondelete={'outgoing_gt': 'cascade', 'internal_ga': 'cascade', 'incoming_gd': 'cascade'}
    )
    picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Operation Type",
        compute="_compute_picking_type_id",
        inverse="_inverse_picking_type_id",
        store=True,
    )
    picking_type_id_domain = fields.Binary(
        string="Picking Type Domain",
        default=[],
        compute='_compute_picking_type_id_domain',
    )

    def write(self, vals):
        for series in self:
            if "picking_type_id" not in vals:
                continue
            if (
                series.picking_type_id
                and self.env['stock.picking'].search_count([
                    ('picking_type_id', '=', series.picking_type_id.id),
                    ('l10n_pt_stock_inalterable_hash', '!=', False),
                ], limit=1)
            ):
                raise UserError(_("You cannot change the AT series of a Picking Type once it has been used."))
            if vals['picking_type_id'] and series.search_count([
                ('picking_type_id', '=', vals.get('picking_type_id')),
                ('id', '!=', series.id),
            ], limit=1):
                raise UserError(_("You cannot use the same AT series for more than one Picking Type."))
        return super().write(vals)

    @api.depends('picking_type_id.l10n_pt_stock_at_series_id')
    def _compute_picking_type_id(self):
        for series in self:
            picking_type = self.env['stock.picking.type'].search([
                ('l10n_pt_stock_at_series_id', '=', series.id)
            ], limit=1)
            series.picking_type_id = picking_type

    def _inverse_picking_type_id(self):
        for series in self:
            if series.picking_type_id:
                series.picking_type_id.l10n_pt_stock_at_series_id = series

    def _compute_picking_type_id_domain(self):
        for at_series in self:
            at_series.picking_type_id_domain = [('code', '=', AT_SERIES_TYPE_MOVEMENT_TYPE_MAP.get(at_series.type))]
