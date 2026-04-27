# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import OrderedSet


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    def action_open_mps_view(self):
        self.ensure_one()
        all_boms = self._get_child_boms()
        action = self.env["ir.actions.actions"]._for_xml_id("mrp_mps.action_mrp_mps")
        action['domain'] = ["|", ('product_id.bom_line_ids.bom_id', 'in', all_boms.ids),
                            "|", ('product_id.variant_bom_ids', 'in', all_boms.ids),
                            "&", ('product_tmpl_id.bom_ids.product_id', '=', False),
                            ('product_tmpl_id.bom_ids', 'in', all_boms.ids)]
        return action

    def _get_child_boms(self, checked_ids=False):
        """ Return self + all child boms. """
        if not checked_ids:
            checked_ids = OrderedSet()
        checked_ids |= self.ids
        unknown_boms = self.bom_line_ids.child_bom_id.filtered(lambda c: c.id not in checked_ids)
        if unknown_boms:
            return self + unknown_boms._get_child_boms(checked_ids)
        return self
