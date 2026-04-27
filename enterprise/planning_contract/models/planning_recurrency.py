# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time

from odoo import models


class PlanningRecurrency(models.Model):
    _inherit = 'planning.recurrency'

    def _get_misc_recurrence_stop(self):
        res = super()._get_misc_recurrence_stop()
        sorted_slots = self.slot_ids.sorted('end_datetime')
        initial_slot, last_slot = sorted_slots[0], sorted_slots[-1]
        end_contract = self.env['hr.contract'].sudo().search_fetch([
            ('employee_id', '=', last_slot.employee_id.id),
            ('state', '=', 'open'),
            ('date_end', '!=', False)
        ], field_names=['date_end'], limit=1).date_end
        end_contract = datetime.combine(end_contract, time.max) if end_contract else res
        # If the initial slot that we are repeating is planned after the end of the resource contract, we generate the slots
        # on out-of-contract dates normally.
        if initial_slot.start_datetime > end_contract:
            return res
        return min(end_contract, res)
