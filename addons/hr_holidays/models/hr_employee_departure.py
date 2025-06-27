# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields, models


class HrEmployeeDeparture(models.Model):
    _inherit = 'hr.employee.departure'

    do_cancel_time_off_requests = fields.Boolean(
        string="Cancel Time Off Requests",
        default=True,
        help="Set the running allocations validity's end and delete future time off.")

    def action_register(self):
        super().action_register()
        cancel_leave_departures = self.filtered(lambda d: d.do_cancel_time_off_requests)
        if not cancel_leave_departures:
            return
        all_leaves_sudo = self.sudo().env['hr.leave'].search([
            ('employee_id', 'in', cancel_leave_departures.employee_id.ids),
            ('date_to', '>', min(cancel_leave_departures.mapped('departure_date'))),
        ])
        all_allocations_sudo = self.sudo().env['hr.leave.allocation'].search([
            ('employee_id', 'in', cancel_leave_departures.employee_id.ids),
            '|',
                ('date_to', '=', False),
                ('date_to', '>', min(cancel_leave_departures.mapped('departure_date'))),
        ])
        for departure in cancel_leave_departures:
            employee_leaves_sudo = all_leaves_sudo.filtered_domain([
                ('employee_id', '=', departure.employee_id.id),
                ('date_to', '>', departure.departure_date),
            ])
            if employee_leaves_sudo:
                leaves_with_departure_sudo = employee_leaves_sudo.filtered(
                    lambda leave: leave.date_from.date() <= departure.departure_date)
                leaves_after_departure_sudo = employee_leaves_sudo - leaves_with_departure_sudo

                new_leaves_sudo = leaves_with_departure_sudo._split_leaves(
                    split_date_from=(departure.departure_date + timedelta(days=1)))
                # Post message for changes leaves
                changes_leaves_sudo = leaves_with_departure_sudo.filtered(lambda leave: leave.date_to.date() <= departure.departure_date)
                changes_msg = self.env._('End date has been updated because '
                    'the employee will leave the company on %(departure_date)s.',
                    departure_date=departure.departure_date,
                )
                for leave in changes_leaves_sudo:
                    leave.message_post(body=changes_msg, message_type="comment", subtype_xmlid="mail.mt_comment")

                # Cancel approved leaves
                leaves_after_departure_sudo += new_leaves_sudo
                leaves_to_cancel_sudo = leaves_after_departure_sudo.filtered(lambda leave: leave.state in ['validate', 'validate1'])
                cancel_msg = self.env._('The employee will leave the company on %(departure_date)s.',
                    departure_date=departure.departure_date)
                leaves_to_cancel_sudo._force_cancel(cancel_msg, notify_responsibles=False)
                # Delete others leaves
                leaves_to_delete_sudo = leaves_after_departure_sudo - leaves_to_cancel_sudo
                leaves_to_delete_sudo.with_context(leave_skip_state_check=True).unlink()

            employee_allocations_sudo = all_allocations_sudo.filtered_domain([
                ('employee_id', '=', departure.employee_id.id),
                '|',
                    ('date_to', '=', False),
                    ('date_to', '>', departure.departure_date),
            ])
            if employee_allocations_sudo:
                to_delete = self.env['hr.leave.allocation']
                to_modify = self.env['hr.leave.allocation']
                allocation_msg = self.env._('Validity End date has been updated because '
                    'the employee will leave the company on %(departure_date)s.',
                    departure_date=departure.departure_date,
                )
                for allocation in employee_allocations_sudo:
                    if allocation.date_from > departure.departure_date:
                        to_delete |= allocation
                    else:
                        to_modify |= allocation
                        allocation.message_post(body=allocation_msg, subtype_xmlid='mail.mt_comment')
                to_delete.with_context(allocation_skip_state_check=True).unlink()
                to_modify.date_to = departure.departure_date

            departure.employee_id.message_post(body=self.env._("Time off and allocation requests have been cleaned for %s", departure.employee_id.name))
