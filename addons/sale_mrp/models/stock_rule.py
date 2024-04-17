# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _get_linked_mo_id(self, procurement, rule, bom):
        # When similar MOs are created through MTSO from SOs, create a MO for each SO, update existing MO if possible
        # However, when they're created from an orderpoint, 'merge them' if possible
        if procurement.values.get('group_id') and procurement.values['group_id'].group_dest_ids.sale_id and not procurement.values.get('orderpoint_id'):
            sale_mo_ids = procurement.values['group_id'].group_dest_ids.sale_id.mrp_production_ids
            mo = sale_mo_ids.filtered(lambda mo: mo.bom_id.id == bom.id and mo.state not in ('done', 'cancel'))
            if len(mo) > 1:
                mo = mo[-1]  # Take the most recent
            if mo:
                return mo
        return super()._get_linked_mo_id(procurement, rule, bom)
