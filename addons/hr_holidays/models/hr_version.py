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
        if self.env.context.get('salary_simulation'):
            return super().create(vals_list)
        all_new_leave_origin = []
        all_new_leave_vals = []
        leaves_state = {}
        created_versions = self.env['hr.version']
<<<<<<< 49484032897eb60a55a3f027265c937e677e39d2
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
                if len(overlapping_contracts.resource_calendar_id) > 1:
                    all_new_leave_origin, all_new_leave_vals = self._populate_all_new_leave_vals_from_split_leave(
                        all_new_leave_origin, all_new_leave_vals, overlapping_contracts, leave, leaves_state)
                else:
                    self._update_leave_calendar(leave, overlapping_contracts)
            # TODO FIXME
            # to keep creation order, not ideal but ok for now.
            if not is_created:
                created_versions |= super().create([vals])
        try:
||||||| 0e22ab8485cf8d00e4fc1f7245f9ceea69fbe0fc
        try:
            for vals in vals_list:
                if not 'employee_id' in vals or not 'resource_calendar_id' in vals:
                    created_versions |= super().create(vals)
                    continue
                leaves = self._get_leaves_from_vals(vals)
                is_created = False
                for leave in leaves:
                    leaves_state = self._refuse_leave(leave, leaves_state)
                    if not is_created:
                        created_versions |= super().create([vals])
                        is_created = True
                    overlapping_contracts = self._check_overlapping_contract(leave)
                    if not overlapping_contracts:
                        continue
                    all_new_leave_origin, all_new_leave_vals = self._populate_all_new_leave_vals_from_split_leave(
                        all_new_leave_origin, all_new_leave_vals, overlapping_contracts, leave, leaves_state)
                # TODO FIXME
                # to keep creation order, not ideal but ok for now.
                if not is_created:
                    created_versions |= super().create([vals])
=======
        try:
            for vals in vals_list:
                if not 'employee_id' in vals or not 'resource_calendar_id' in vals:
                    created_versions |= super().create(vals)
                    continue
                leaves = self._get_leaves_from_vals(vals)
                for leave in leaves:
                    leaves_state = self._refuse_leave(leave, leaves_state)
                created_versions |= super().create([vals])
                for leave in leaves:
                    overlapping_contracts = self._check_overlapping_contract(leave)
                    if not overlapping_contracts:
                        continue
                    all_new_leave_origin, all_new_leave_vals = self._populate_all_new_leave_vals_from_split_leave(
                        all_new_leave_origin, all_new_leave_vals, overlapping_contracts, leave, leaves_state)
>>>>>>> 5905f812fd58714e4569b5d22216dc4874409602
            if all_new_leave_vals:
                self._create_all_new_leave(all_new_leave_origin, all_new_leave_vals)
        except ValidationError as e:
            # In case a validation error is thrown due to holiday creation with the new resource calendar (which can
            # increase their duration), we catch this error to display a more meaningful error message.
            raise ValidationError(
                self.env._("Changing the contract on this employee changes their working schedule in a period "
                           "they already took leaves. Changing this working schedule changes the duration of "
                           "these leaves in such a way the employee no longer has the required allocation for "
                           "them. Please review these leaves and/or allocations before changing the contract.\n\n"
                           "This error has been triggered by:\n") + str(e))
        return created_versions

    def write(self, vals):
<<<<<<< 49484032897eb60a55a3f027265c937e677e39d2
        # we do not want to run this logic if these fields were not affected or if we are in a simulated contract
        if not any(field in vals for field in ['contract_date_start', 'contract_date_end', 'date_version', 'resource_calendar_id']) or self.env.context.get('salary_simulation'):
            return super().write(vals)
||||||| 0e22ab8485cf8d00e4fc1f7245f9ceea69fbe0fc
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
                        super(HrVersion, contract).write(vals)
                        overlapping_contracts = self._check_overlapping_contract(leave)
                        if not overlapping_contracts:
                            continue
                        leaves_state = self._refuse_leave(leave, leaves_state)
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
=======
        specific_contracts = self.env['hr.version']
        if any(field in vals for field in ['contract_date_start', 'contract_date_end', 'date_version', 'resource_calendar_id']):
            all_new_leave_origin = []
            all_new_leave_vals = []
            leaves_state = {}
            try:
                for contract in self:
                    resource_calendar_id = vals.get('resource_calendar_id', contract.resource_calendar_id.id)
                    extra_domain = [('resource_calendar_id', '!=', resource_calendar_id)] if resource_calendar_id else None
                    leaves = contract.with_context(contract_date_start=vals.get('contract_date_start', False))._get_leaves(
                        extra_domain=extra_domain
                    )
                    for leave in leaves:
                        overlapping_contracts = contract.with_context(version_write_vals=vals)._check_overlapping_contract(leave)
                        if not overlapping_contracts:
                            continue
                        leaves_state = self._refuse_leave(leave, leaves_state)
                        super(HrVersion, contract).write(vals)
                        specific_contracts += contract
                        all_new_leave_origin, all_new_leave_vals = self._populate_all_new_leave_vals_from_split_leave(
                            all_new_leave_origin, all_new_leave_vals, overlapping_contracts | contract, leave, leaves_state)
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
>>>>>>> 5905f812fd58714e4569b5d22216dc4874409602

        all_new_leave_origin = []
        all_new_leave_vals = []
        leaves_state = {}

        # Pre-fetch leaves per contract BEFORE write, using post-write effective dates
        # so we don't pull leaves outside the version's effective period.
        contract_leaves = {}
        for contract in self:
            resource_calendar_id = vals.get('resource_calendar_id', contract.resource_calendar_id.id)
            extra_domain = [('resource_calendar_id', '!=', resource_calendar_id)] if resource_calendar_id else None
            new_date_version = fields.Date.from_string(vals.get('date_version') or contract.date_version)
            new_contract_date_start = fields.Date.from_string(
                vals.get('contract_date_start') or contract.sudo().contract_date_start or new_date_version
            )
            min_date = max(new_contract_date_start, new_date_version)
            contract_leaves[contract.id] = contract._get_leaves(extra_domain=extra_domain, min_date=min_date)

        result = super().write(vals)

        # Process leaves now that DB reflects new contract state
        for contract in self:
            for leave in contract_leaves[contract.id]:
                overlapping_contracts = self._check_overlapping_contract(leave)
                if len(overlapping_contracts.resource_calendar_id) > 1:
                    leaves_state = self._update_leave_state(leave, leaves_state, True)
                    all_new_leave_origin, all_new_leave_vals = self._populate_all_new_leave_vals_from_split_leave(
                        all_new_leave_origin, all_new_leave_vals, overlapping_contracts, leave, leaves_state)
                else:
                    self._update_leave_calendar(leave, overlapping_contracts)

        try:
            if all_new_leave_vals:
                self._create_all_new_leave(all_new_leave_origin, all_new_leave_vals)
        except ValidationError as e:
            # In case a validation error is thrown due to holiday creation with the new resource calendar (which can
            # increase their duration), we catch this error to display a more meaningful error message.
            raise ValidationError(
                self.env._("Changing the contract on this employee changes their working schedule in a period "
                           "they already took leaves. Changing this working schedule changes the duration of "
                           "these leaves in such a way the employee no longer has the required allocation for "
                           "them. Please review these leaves and/or allocations before changing the contract.\n\n"
                           "This error has been triggered by:\n") + str(e))

        return result

    def _get_leaves(self, extra_domain=None, min_date=None):
        if min_date is None:
            min_date = min(
                max(c.contract_date_start or c.date_version, c.date_version)
                for c in self.sudo()
            )
        domain = [
            ('state', '!=', 'refuse'),
<<<<<<< 49484032897eb60a55a3f027265c937e677e39d2
            ('employee_id', 'in', self.employee_id.ids),
            ('date_to', '>=', min_date),
||||||| 0e22ab8485cf8d00e4fc1f7245f9ceea69fbe0fc
            ('employee_id', 'in', self.mapped('employee_id.id')),
            ('date_from', '<=', max(end or date.max for end in self.sudo().mapped('contract_date_end'))),
            ('date_to', '>=', min(self.sudo().mapped('contract_date_start'))),
=======
            ('employee_id', 'in', self.mapped('employee_id.id')),
            ('date_from', '<=', max(end or date.max for end in self.sudo().mapped('contract_date_end'))),
            ('date_to', '>=', fields.Date.from_string(self.env.context.get('contract_date_start', False)) or min(self.sudo().mapped('contract_date_start'))),
>>>>>>> 5905f812fd58714e4569b5d22216dc4874409602
        ]
        if extra_domain:
            domain = Domain.AND([domain, extra_domain])
        return self.env['hr.leave'].search(domain)

    def _get_leaves_from_vals(self, vals):
        contract_date_start = fields.Date.from_string(vals.get('contract_date_start') or vals.get('date_version', fields.Date.today()))
        version_date_start = fields.Date.from_string(vals.get('date_version', fields.Date.today()))
        relevant_start_date = max(contract_date_start, version_date_start)
        domain = [
            ('state', 'not in', ['refuse', 'cancel']),
            ('employee_id', 'in', vals['employee_id']),
            ('date_to', '>=', relevant_start_date),
            ('resource_calendar_id', '!=', vals.get('resource_calendar_id')),
        ]
        if vals.get('contract_date_end'):
            domain = Domain.AND([domain, [('date_from', '<=', fields.Date.from_string(vals['contract_date_end']))]])
        return self.env['hr.leave'].search(domain)

    def _check_overlapping_contract(self, leave):
<<<<<<< 49484032897eb60a55a3f027265c937e677e39d2
        return leave._get_overlapping_contracts().sorted(key=lambda c: c.contract_date_start)
||||||| 0e22ab8485cf8d00e4fc1f7245f9ceea69fbe0fc
        # Get all overlapping contracts but exclude draft contracts that are not included in this transaction.
        overlapping_contracts = leave._get_overlapping_contracts().sorted(
            key=lambda c: c.contract_date_start)
        if len(overlapping_contracts.resource_calendar_id) <= 1:
            if overlapping_contracts:
                first_overlapping_contract = next(iter(overlapping_contracts), overlapping_contracts)
                if leave.resource_calendar_id != first_overlapping_contract.resource_calendar_id:
                    leave.resource_calendar_id = first_overlapping_contract.resource_calendar_id
                    if not leave.request_unit_hours:
                        leave.with_context(leave_skip_date_check=True, leave_skip_state_check=True)._compute_date_from_to()
                        if leave.state == 'validate':
                            leave._validate_leave_request()
            return False
        return overlapping_contracts
=======
        # Get all overlapping contracts but exclude draft contracts that are not included in this transaction.
        overlapping_contracts = leave._get_overlapping_contracts().sorted(
            key=lambda c: c.date_start)
        version_write_vals = self.env.context.get('version_write_vals', {})
        context_calendar = self.env['resource.calendar'].browse(version_write_vals.get('resource_calendar_id', False))
        all_calendars = overlapping_contracts.resource_calendar_id if not context_calendar else (overlapping_contracts - self).resource_calendar_id | context_calendar
        if len(all_calendars) <= 1:
            if overlapping_contracts:
                first_overlapping_contract = next(iter(overlapping_contracts), overlapping_contracts)
                new_calendar = context_calendar or first_overlapping_contract.resource_calendar_id
                if leave.resource_calendar_id != new_calendar:
                    leave.resource_calendar_id = new_calendar
                    if not leave.request_unit_hours:
                        leave.with_context(leave_skip_date_check=True, leave_skip_state_check=True, leave_skip_calendar_recompute=True)._compute_date_from_to()
                        if leave.state == 'validate':
                            leave._validate_leave_request()
            return False
        return overlapping_contracts
>>>>>>> 5905f812fd58714e4569b5d22216dc4874409602

    def _update_leave_calendar(self, leave, overlapping_contracts):
        if not overlapping_contracts:
            return
        first_contract = overlapping_contracts[0]
        if leave.resource_calendar_id == first_contract.resource_calendar_id:
            return
        leave.resource_calendar_id = first_contract.resource_calendar_id
        if leave.work_entry_type_request_unit != 'hour':
            leave.with_context(leave_skip_date_check=True, leave_skip_state_check=True)._compute_date_from_to()
            if leave.state == 'validate':
                leave._validate_leave_request()

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
            new_request_date_from = max(leave.request_date_from, overlapping_contract.date_start)
            new_request_date_to = min(leave.request_date_to, overlapping_contract.date_end or date.max)
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
