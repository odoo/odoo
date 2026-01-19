# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, UTC
from odoo import api, fields, models
from odoo.fields import Domain
from odoo.exceptions import ValidationError


class HrVersion(models.Model):
    """ Write and Create:
        Special case when setting a contract as running:
        If there is already a validated time off over another contract
        with a different schedule, split the time off, before the
        _check_contracts raises an issue.
        If there are existing leaves that are spanned by this new
        contract, update their resource calendar to the current one.
    """
    # TODO BIOUTIFY ME (the whole file :)
    _inherit = 'hr.version'
    _description = 'Employee Contract'

    departure_do_cancel_time_off_requests = fields.Boolean(related='departure_id.do_cancel_time_off_requests')

    @api.constrains('contract_date_start', 'contract_date_end')
    def _check_contracts(self):
        self._get_leaves()._check_contracts()

    @api.model_create_multi
    def create(self, vals_list):
        all_new_leave_origin = []
        all_new_leave_vals = []
        leaves_state = {}
        created_versions = self.env['hr.version']
        for vals in vals_list:
            if not 'employee_id' in vals or not 'resource_calendar_id' in vals:
                created_versions |= super().create(vals)
                continue
            leaves = self._get_leaves_from_vals(vals)
            is_created = False
            for leave in leaves:
                leaves_state = self._update_leave_state(leave, leaves_state, leave.request_date_from < vals['contract_date_start'])
                if not is_created:
                    created_versions |= super().create([vals])
                    is_created = True
                overlapping_contracts = self._check_overlapping_contract(leave)
                if not overlapping_contracts:
                    # When the leave is set to draft
                    leave._compute_date_from_to()
                    continue
                all_new_leave_origin, all_new_leave_vals = self._populate_all_new_leave_vals_from_split_leave(
                    all_new_leave_origin, all_new_leave_vals, overlapping_contracts, leave, leaves_state)
            # TODO FIXME
            # to keep creation order, not ideal but ok for now.
            if not is_created:
                created_versions |= super().create([vals])
        try:
            if all_new_leave_vals:
                self._create_all_new_leave(all_new_leave_origin, all_new_leave_vals)
        except ValidationError:
            # In case a validation error is thrown due to holiday creation with the new resource calendar (which can
            # increase their duration), we catch this error to display a more meaningful error message.
            raise ValidationError(
                self.env._("Changing the contract on this employee changes their working schedule in a period "
                           "they already took leaves. Changing this working schedule changes the duration of "
                           "these leaves in such a way the employee no longer has the required allocation for "
                           "them. Please review these leaves and/or allocations before changing the contract."))
        return created_versions

    def write(self, vals):
        specific_contracts = self.env['hr.version']
        if any(field in vals for field in ['contract_date_start', 'contract_date_end', 'date_version', 'resource_calendar_id']):
            all_new_leave_origin = []
            all_new_leave_vals = []
            leaves_state = {}
            try:
                for contract in self:
                    resource_calendar_id = vals.get('resource_calendar_id', contract.resource_calendar_id.id)
                    extra_domain = [('resource_calendar_id', '!=', resource_calendar_id)] if resource_calendar_id else None
                    leaves = contract._get_leaves(
                        extra_domain=extra_domain
                    )
                    for leave in leaves:
                        overlapping_contracts = self._check_overlapping_contract(leave)
                        if not overlapping_contracts:
                            continue
                        leaves_state = self._update_leave_state(leave, leaves_state, True)
                        super(HrVersion, contract).write(vals)
                        specific_contracts += contract
                        all_new_leave_origin, all_new_leave_vals = self._populate_all_new_leave_vals_from_split_leave(
                            all_new_leave_origin, all_new_leave_vals, overlapping_contracts, leave, leaves_state)
                if all_new_leave_vals:
                    self._create_all_new_leave(all_new_leave_origin, all_new_leave_vals)
            except ValidationError:
                # In case a validation error is thrown due to holiday creation with the new resource calendar (which can
                # increase their duration), we catch this error to display a more meaningful error message.
                raise ValidationError(self.env._("Changing the contract on this employee changes their working schedule in a period "
                                        "they already took leaves. Changing this working schedule changes the duration of "
                                        "these leaves in such a way the employee no longer has the required allocation for "
                                        "them. Please review these leaves and/or allocations before changing the contract."))
        return super(HrVersion, self - specific_contracts).write(vals)

    def _get_leaves(self, extra_domain=None):
        domain = [
            ('state', '!=', 'refuse'),
            ('employee_id', 'in', self.mapped('employee_id.id')),
            ('date_from', '<=', max(end or date.max for end in self.sudo().mapped('contract_date_end'))),
            ('date_to', '>=', min(self.sudo().mapped('contract_date_start'))),
        ]
        if extra_domain:
            domain = Domain.AND([domain, extra_domain])
        return self.env['hr.leave'].search(domain)

    def _get_leaves_from_vals(self, vals):
        domain = [
            ('state', '!=', 'refuse'),
            ('employee_id', 'in', vals['employee_id']),
            ('date_to', '>=', fields.Date.from_string(vals.get('contract_date_start', vals.get('date_version', fields.Date.today())))),
            ('resource_calendar_id', '!=', vals.get('resource_calendar_id')),
        ]
        if vals.get('contract_date_end'):
            domain = Domain.AND([domain, [('date_from', '<=', fields.Date.from_string(vals['contract_date_end']))]])
        return self.env['hr.leave'].search(domain)

    def _check_overlapping_contract(self, leave):
        # Get all overlapping contracts but exclude draft contracts that are not included in this transaction.
        overlapping_contracts = leave._get_overlapping_contracts().sorted(
            key=lambda c: c.contract_date_start)
        if len(overlapping_contracts.resource_calendar_id) <= 1:
            if overlapping_contracts:
                first_overlapping_contract = next(iter(overlapping_contracts), overlapping_contracts)
                if leave.resource_calendar_id != first_overlapping_contract.resource_calendar_id:
                    leave.resource_calendar_id = first_overlapping_contract.resource_calendar_id
            return False
        return overlapping_contracts

    def _update_leave_state(self, leave, leaves_state, refuse_leave=False):
        if leave.id not in leaves_state:
            leaves_state[leave.id] = leave.state
        if leave.state not in ['refuse', 'confirm']:
            if refuse_leave:
                leave.action_refuse()
            else:
                leave.action_back_to_approval()
        return leaves_state

    def _populate_all_new_leave_vals_from_split_leave(self, all_new_leave_origin, all_new_leave_vals, overlapping_contracts, leave, leaves_state):
        last_version = overlapping_contracts[-1]
        for overlapping_contract in overlapping_contracts:
            new_request_date_from = max(leave.request_date_from, overlapping_contract.contract_date_start)
            new_request_date_to = min(leave.request_date_to, overlapping_contract.contract_date_end or date.max)
            new_leave_vals = leave.copy_data({
                'request_date_from': new_request_date_from,
                'request_date_to': new_request_date_to,
                'state': leaves_state[leave.id] if overlapping_contract.id != last_version.id else 'confirm',
            })[0]
            new_leave = self.env['hr.leave'].new(new_leave_vals)
            new_leave._compute_date_from_to()
            new_leave._compute_duration()
            # Could happen for part-time contract, that time off is not necessary
            # anymore.
            if new_leave.date_from < new_leave.date_to:
                all_new_leave_origin.append(leave)
                all_new_leave_vals.append(new_leave._convert_to_write(new_leave._cache))
        return all_new_leave_origin, all_new_leave_vals

    def _create_all_new_leave(self, all_new_leave_origin, all_new_leave_vals):
        new_leaves = self.env['hr.leave'].with_context(
            tracking_disable=True,
            mail_activity_automation_skip=True,
            leave_fast_create=True,
            leave_skip_state_check=True
        ).create(all_new_leave_vals)
        new_leaves.filtered(lambda l: l.state in 'validate')._validate_leave_request()
        for index, new_leave in enumerate(new_leaves):
            new_leave.message_post_with_source(
                'mail.message_origin_link',
                render_values={'self': new_leave, 'origin': all_new_leave_origin[index]},
                subtype_xmlid='mail.mt_note',
            )

    # override to add work_entry_type from leave
    def _get_leave_work_entry_type(self, leave):
        if leave.holiday_id:
            return leave.holiday_id.work_entry_type_id
        else:
            return leave.work_entry_type_id

    def _get_more_vals_leave_interval(self, interval, leaves):
        result = super()._get_more_vals_leave_interval(interval, leaves)
        for leave in leaves:
            if interval[0] >= leave[0] and interval[1] <= leave[1]:
                if leave[2].holiday_id:
                    result.append(('leave_ids', leave[2].holiday_id))
        return result

    def _get_interval_leave_work_entry_type(self, interval, leaves, bypassing_codes):
        # returns the work entry time related to the leave that
        # includes the whole interval.
        # Overriden in hr_work_entry_holiday to select the
        # global time off first (eg: Public Holiday > Home Working)
        self.ensure_one()
        if 'work_entry_type_id' in interval[2]:
            work_entry_types = interval[2].work_entry_type_id
            if work_entry_types and work_entry_types[:1].code in bypassing_codes:
                return work_entry_types[:1]

        interval_start = interval[0].astimezone(UTC).replace(tzinfo=None)
        interval_stop = interval[1].astimezone(UTC).replace(tzinfo=None)
        including_rcleaves = [l[2] for l in leaves if l[2] and interval_start >= l[2][0].date_from and interval_stop <= l[2][0].date_to]
        including_global_rcleaves = [l for l in including_rcleaves if not l.holiday_id]
        including_holiday_rcleaves = [l for l in including_rcleaves if l.holiday_id]
        rc_leave = False

        # Example: In CP200: Long term sick > Public Holidays (which is global)
        if bypassing_codes:
            bypassing_rc_leave = [l for l in including_holiday_rcleaves if l.holiday_id.work_entry_type_id.code in bypassing_codes]
        else:
            bypassing_rc_leave = []

        if bypassing_rc_leave:
            rc_leave = bypassing_rc_leave[0]
        elif including_global_rcleaves:
            rc_leave = including_global_rcleaves[0]
        elif including_holiday_rcleaves:
            rc_leave = including_holiday_rcleaves[0]
        if rc_leave:
            return self._get_leave_work_entry_type_dates(rc_leave, interval_start, interval_stop, self.employee_id)
        return self.env.ref('hr_work_entry.generic_work_entry_type_leave')

    def _get_sub_leave_domain(self):
        # see https://github.com/odoo/enterprise/pull/15091
        return super()._get_sub_leave_domain() | Domain('holiday_id.employee_id', 'in', self.employee_id.ids)

    @api.model
    def _generate_work_entries_postprocess_adapt_to_calendar(self, vals):
        res = super()._generate_work_entries_postprocess_adapt_to_calendar(vals)
        if 'work_entry_type_id' not in vals or not vals.get('leave_ids'):
            return res
        work_entry_type = vals['work_entry_type_id']
        return res or (work_entry_type.count_as == 'absence' or work_entry_type.request_unit != 'hour')

    @api.model
    def _get_work_entry_source_fields(self):
        return super()._get_work_entry_source_fields() + ['leave_ids']
