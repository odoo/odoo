# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class MrpConsumptionWarning(models.TransientModel):
    _inherit = 'mrp.consumption.warning'

    def action_confirm(self):
        if self.mrp_production_ids._get_subcontract_move():
            return self.mrp_production_ids.with_context(skip_consumption=True).subcontracting_record_component()
        return super().action_confirm()

    def action_cancel(self):
        mo_subcontracted_move = self.mrp_production_ids._get_subcontract_move()
        if mo_subcontracted_move:
            return mo_subcontracted_move.filtered(lambda move: move.state not in ('done', 'cancel'))._action_record_components()
        return super().action_cancel()
