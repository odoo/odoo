# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

# fields that when changed invalidate previously credited allocations
_TIME_FIELDS = frozenset({'check_in', 'check_out', 'employee_id'})

# states in which an attendance no longer counts as valid source material
_INVALID_STATES = frozenset({'refused', 'draft'})


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    def _get_work_entry_type_domain(self, country_ids=None):
        return super()._get_work_entry_type_domain(country_ids=country_ids) + [('requires_allocation', '=', False)]

    def write(self, vals):
        """Reverse the allocation credits logged on the attendances before an invalidating
        write.

        Credits are reversed when ``check_in``, ``check_out`` or ``employee_id`` change (unless
        the context has ``skip_time_rules``), or when a validated attendance goes back to
        ``draft`` or is ``refused``. Re-running the rules credits the new values again.

        :raise ValidationError: if the allocation was already used beyond its allowed balance
        """
        to_reverse = set()
        if not self.env.context.get('skip_time_rules') and _TIME_FIELDS & vals.keys():
            to_reverse.update(self.ids)
        if vals.get('state') in _INVALID_STATES:
            to_reverse.update(self.filtered(lambda a: a.state == 'validated').ids)
        if to_reverse:
            self.env['hr.time.rule']._reverse_allocation_credits('hr.attendance', to_reverse)
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _reverse_credits_on_unlink(self):
        """Reverse the allocation credits logged on the deleted attendances."""
        self.env['hr.time.rule']._reverse_allocation_credits('hr.attendance', self.ids)
