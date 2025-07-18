# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
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

    @api.constrains('contract_date_start', 'contract_date_end')
    def _check_contracts(self):
        self._get_leaves()._check_contracts()

    @api.model_create_multi
    def create(self, vals_list):
        all_new_leave_origin = []
        all_new_leave_vals = []
        leaves_state = {}
        created_versions = self.env['hr.version']
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
                    leaves = contract.sudo()._get_leaves(
                        extra_domain=extra_domain
                    )
                    for leave in leaves:
                        overlapping_contracts = self._check_overlapping_contract(leave)
                        if not overlapping_contracts:
                            continue
                        leaves_state = self._refuse_leave(leave, leaves_state)
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
            ('date_from', '<=', max(end or date.max for end in self.mapped('date_end'))),
            ('date_to', '>=', min(self.mapped('date_start'))),
        ]
        if extra_domain:
            domain = Domain.AND([domain, extra_domain])
        return self.env['hr.leave'].search(domain)

    def _get_leaves_from_vals(self, vals):
        domain = [
            ('state', '!=', 'refuse'),
            ('employee_id', 'in', vals['employee_id']),
            ('date_to', '>=', fields.Date.from_string(vals.get('contract_date_start', vals['date_version']))),
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
            if overlapping_contracts and leave.resource_calendar_id != overlapping_contracts[
                0].resource_calendar_id:
                leave.resource_calendar_id = overlapping_contracts[0].resource_calendar_id
            return False
        return overlapping_contracts

    def _refuse_leave(self, leave, leaves_state):
        if leave.id not in leaves_state:
            leaves_state[leave.id] = leave.state
        if leave.state != 'refuse':
            leave.action_refuse()
        return leaves_state

    def _populate_all_new_leave_vals_from_split_leave(self, all_new_leave_origin, all_new_leave_vals, overlapping_contracts, leave, leaves_state):
        for overlapping_contract in overlapping_contracts:
            new_request_date_from = max(leave.request_date_from, overlapping_contract.contract_date_start)
            new_request_date_to = min(leave.request_date_to, overlapping_contract.contract_date_end or date.max)
            new_leave_vals = leave.copy_data({
                'request_date_from': new_request_date_from,
                'request_date_to': new_request_date_to,
                'state': leaves_state[leave.id],
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
