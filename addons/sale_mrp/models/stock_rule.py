# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_linked_mo_id(self, procurement, rule, bom):
        # When similar MOs are created through MTSO from SOs, create a MO for each SO, update existing MO if possible
        # However, when they're created from an orderpoint, 'merge them' if possible
        if procurement.values.get('group_id') and procurement.values['group_id'].get('group_dest_ids') and procurement.values['group_id'].get('group_dest_ids').sale_id and not procurement.values.get('orderpoint_id'):
            sale_mo_ids = procurement.values['group_id'].sale_ids.mrp_production_ids
            mo = sale_mo_ids.filtered(lambda mo: mo.bom_id.id == bom.id and mo.state not in ('done', 'cancel'))
            if len(mo) > 1:
                mo = mo[-1]  # Take the most recent
            if mo:
                return mo
        return super()._get_linked_mo_id(procurement, rule, bom)

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, bom):
        mo_values = super()._prepare_mo_vals(product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, bom)
        if not mo_values.get('procurement_group_id') and values.get('move_dest_ids') and values.get('group_id') and values['move_dest_ids'][0].procure_method == 'make_to_stock' and values['group_id'].sale_ids:  # FIXME : (first found with matching criteria instead of index 0 ?)
            mo_values['name'] = self.env['stock.picking.type'].browse(mo_values['picking_type_id']).sequence_id.next_by_id()
            procurement_group_vals = self.env['mrp.production']._prepare_procurement_group_vals(mo_values)
            procurement_group_vals['sale_ids'] = [Command.link(values['group_id'].sale_ids[0].id)]  # FIXME : index may be falsy
            mo_values['procurement_group_id'] = self.env["procurement.group"].create(procurement_group_vals).id
        return mo_values
