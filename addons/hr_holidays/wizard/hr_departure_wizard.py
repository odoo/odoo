# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import _, models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    def action_register_departure(self):
        action = super().action_register_departure()
        employee_leaves = self.env['hr.leave'].search([
            ('employee_id', 'in', self.employee_ids.ids),
            ('date_to', '>', self.departure_date),
        ])

        if employee_leaves:
            leaves_with_departure = employee_leaves.filtered(
                lambda leave: leave.date_from.date() <= self.departure_date)
            leaves_after_departure = employee_leaves - leaves_with_departure

            new_leaves = leaves_with_departure._split_leaves(
                split_date_from=(self.departure_date + timedelta(days=1)))
            # Post message for changes leaves
            changes_leaves = leaves_with_departure.filtered(lambda leave: leave.date_to.date() <= self.departure_date)
            changes_msg = _('End date has been updated because '
                'the employee will leave the company on %(departure_date)s.',
                departure_date=self.departure_date
            )
            for leave in changes_leaves:
                leave.message_post(body=changes_msg, message_type="comment", subtype_xmlid="mail.mt_comment")

            # Cancel approved leaves
            leaves_after_departure |= leaves_with_departure - changes_leaves
            leaves_after_departure |= new_leaves
            leaves_to_cancel = leaves_after_departure.filtered(lambda leave: leave.state in ['validate', 'validate1'])
            cancel_msg = _('The employee will leave the company on %(departure_date)s.',
                departure_date=self.departure_date)
            leaves_to_cancel._force_cancel(cancel_msg, notify_responsibles=False)
            # Delete others leaves
            leaves_to_delete = leaves_after_departure - leaves_to_cancel
            leaves_to_delete.with_context(leave_skip_state_check=True).unlink()

        employee_allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', 'in', self.employee_ids.ids),
            '|',
                ('date_to', '=', False),
                ('date_to', '>', self.departure_date),
        ])
        if not employee_allocations:
            return action
        to_delete = self.env['hr.leave.allocation']
        to_modify = self.env['hr.leave.allocation']
        allocation_msg = _('Validity End date has been updated because '
            'the employee will leave the company on %(departure_date)s.',
            departure_date=self.departure_date
        )
        for allocation in employee_allocations:
            if allocation.date_from > self.departure_date:
                to_delete |= allocation
            else:
                to_modify |= allocation
                allocation.message_post(body=allocation_msg, subtype_xmlid='mail.mt_comment')
        to_delete.with_context(allocation_skip_state_check=True).unlink()
        to_modify.date_to = self.departure_date

        return action
