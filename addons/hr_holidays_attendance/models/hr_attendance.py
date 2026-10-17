# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

# fields that when changed invalidate previously credited allocations
_TIME_FIELDS = frozenset({'check_in', 'check_out', 'employee_id'})

# states in which an attendance no longer counts as valid source material
_INVALID_STATES = frozenset({'refused', 'draft'})


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    def write(self, vals):
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
        self.env['hr.time.rule']._reverse_allocation_credits('hr.attendance', self.ids)

    @api.ondelete(at_uninstall=False)
    def _cleanup_orphaned_sources_on_unlink(self):
        if self.env.context.get('skip_time_rules'):
            return
        orphaned = self._get_orphaned_sources_on_unlink()
        if not orphaned:
            return
        # clear fk first, outputs still exist and would block source deletion
        src_field = self._time_rule_source_field
        self.with_context(active_test=False, skip_time_rules=True).write({src_field: False})
        orphaned.with_context(active_test=False, skip_time_rules=True).sudo().unlink()

    def _time_rule_wizard_extra_domain(self):
        return [('state', '=', 'validated')]

    def action_reprocess_time_rules(self):
        return self.env['hr.time.rule.regenerate.wizard'].action_open_from_records(self)
