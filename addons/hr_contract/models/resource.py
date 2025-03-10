# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from datetime import datetime

from odoo import _, api, fields, models
from odoo.osv.expression import AND


class ResourceCalendar(models.Model):
    _inherit = 'resource.calendar'

    # contracts_count = fields.Integer("# Contracts using it", compute='_compute_contracts_count', groups="hr_contract.group_hr_contract_manager")
    # running_contracts_count = fields.Integer("Running contracts count", compute='_compute_contracts_count',
    #     groups="hr_contract.group_hr_contract_manager", search="_search_running_contracts_count")
    # contract_ids = fields.One2many('hr.contract', 'resource_calendar_id', groups="hr_contract.group_hr_contract_manager")

    def transfer_leaves_to(self, other_calendar, resources=None, from_date=None):
        """
            Transfer some resource.calendar.leaves from 'self' to another calendar 'other_calendar'.
            Transfered leaves linked to `resources` (or all if `resources` is None) and starting
            after 'from_date' (or today if None).
        """
        from_date = from_date or fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        domain = [
            ('calendar_id', 'in', self.ids),
            ('date_from', '>=', from_date),
        ]
        domain = AND([domain, [('resource_id', 'in', resources.ids)]]) if resources else domain

        self.env['resource.calendar.leaves'].search(domain).write({
            'calendar_id': other_calendar.id,
        })

    # @api.depends('contract_ids', 'contract_ids.state')
    # def _compute_contracts_count(self):
    #     contracts_data = self.env['hr.contract']._read_group(
    #         domain=[
    #             ('resource_calendar_id', 'in', self.ids),
    #             ('company_id', 'in', self.env.companies.ids),
    #             ('employee_id', '!=', False)],
    #         groupby=['resource_calendar_id', 'state'],
    #         aggregates=['__count']
    #     )
    #     total_contracts_count = defaultdict(int)
    #     running_contracts_count = defaultdict(int)
    #     for calendar, state, count in contracts_data:
    #         if state == 'open':
    #             running_contracts_count[calendar.id] = count
    #         total_contracts_count[calendar.id] += count
    #     for calendar in self:
    #         calendar.contracts_count = total_contracts_count[calendar.id]
    #         calendar.running_contracts_count = running_contracts_count[calendar.id]

    # @api.model
    # def _search_running_contracts_count(self, operator, value):
    #     if operator not in ['=', '!=', '<', '>'] or not isinstance(value, int):
    #         raise NotImplementedError(_('Operation not supported.'))
    #     calendar_ids = self.env['resource.calendar'].search([])
    #     if operator == '=':
    #         calender = calendar_ids.filtered(lambda m: m.running_contracts_count == value)
    #     elif operator == '!=':
    #         calender = calendar_ids.filtered(lambda m: m.running_contracts_count != value)
    #     elif operator == '<':
    #         calender = calendar_ids.filtered(lambda m: m.running_contracts_count < value)
    #     elif operator == '>':
    #         calender = calendar_ids.filtered(lambda m: m.running_contracts_count > value)
    #     return [('id', 'in', calender.ids)]

    def action_open_contracts(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_contract.action_hr_contract")
        action.update({'domain': [('resource_calendar_id', '=', self.id), ('employee_id', '!=', False)]})
        return action
