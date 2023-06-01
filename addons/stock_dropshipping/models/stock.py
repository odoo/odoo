# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class StockRule(models.Model):
    _inherit = 'stock.rule'

    @api.model
    def _get_procurements_to_merge_groupby(self, procurement):
        """ Do not group purchase order line if they are linked to different
        sale order line. The purpose is to compute the delivered quantities.
        """
        return procurement.values.get('sale_line_id'), super(StockRule, self)._get_procurements_to_merge_groupby(procurement)


class ProcurementGroup(models.Model):
    _inherit = "procurement.group"

    @api.model
    def _get_rule_domain(self, location, values):
        if 'sale_line_id' in values and values.get('company_id'):
            return [('location_dest_id', '=', location.id), ('action', '!=', 'push'), ('company_id', '=', values['company_id'].id)]
        else:
            return super(ProcurementGroup, self)._get_rule_domain(location, values)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_dropship = fields.Boolean("Is a Dropship", compute='_compute_is_dropship')

    @api.depends('location_dest_id.usage', 'location_id.usage')
    def _compute_is_dropship(self):
        for picking in self:
            picking.is_dropship = picking.location_dest_id.usage == 'customer' and picking.location_id.usage == 'supplier'

    def _is_to_external_location(self):
        self.ensure_one()
        return super()._is_to_external_location() or self.is_dropship

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    code = fields.Selection(
        selection_add=[('dropship', 'Dropship')], ondelete={'dropship': 'cascade'})

    @api.depends('default_location_src_id', 'default_location_dest_id')
    def _compute_warehouse_id(self):
        super()._compute_warehouse_id()
        if self.default_location_src_id.usage == 'supplier' and self.default_location_dest_id.usage == 'customer':
            self.warehouse_id = False

    @api.depends('code')
    def _compute_show_picking_type(self):
        super()._compute_show_picking_type()
        for record in self:
            if record.code == "dropship":
                record.show_picking_type = True


class StockLot(models.Model):
    _inherit = 'stock.lot'

    def _compute_delivery_ids(self):
        super()._compute_delivery_ids()
        for lot in self:
            if lot.delivery_count > 0:
                last_delivery = max(lot.delivery_ids, key=lambda d: d.date_done)
                if last_delivery.is_dropship:
                    lot.last_delivery_partner_id = last_delivery.sale_id.partner_id

    def _get_delivery_ids_by_lot_domain(self):
        return [
            ('lot_id', 'in', self.ids),
            ('state', '=', 'done'),
            '|',
            '|', ('picking_code', '=', 'outgoing'), ('produce_line_ids', '!=', False),
            # dropship transfers have an incoming picking_code but should be considered as well
            ('location_dest_id.usage', '=', 'customer'), ('location_id.usage', '=', 'supplier')
        ]
