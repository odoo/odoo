# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import api, models, _
from odoo.exceptions import ValidationError
from odoo.osv.expression import AND
from odoo.tools import format_date


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _compute_resource_calendar_id(self):
        super()._compute_resource_calendar_id()
        for leave in self.filtered(lambda l: l.employee_id):
            # We use the request dates to find the contracts, because date_from
            # and date_to are not set yet at this point. Since these dates are
            # used to get the contracts for which these leaves apply and
            # contract start- and end-dates are just dates (and not datetimes)
            # these dates are comparable.
            if leave.employee_id:
                contracts = self.env['hr.contract'].search([
                    '|', ('state', 'in', ['open', 'close']),
                         '&', ('state', '=', 'draft'),
                              ('kanban_state', '=', 'done'),
                    ('employee_id', '=', leave.employee_id.id),
                    ('date_start', '<=', leave.request_date_to),
                    '|', ('date_end', '=', False),
                         ('date_end', '>=', leave.request_date_from),
                ])
                if contracts:
                    # If there are more than one contract they should all have the
                    # same calendar, otherwise a constraint is violated.
                    leave.resource_calendar_id = contracts[:1].resource_calendar_id

    def _get_overlapping_contracts(self, contract_states=None):
        self.ensure_one()
        if contract_states is None:
            contract_states = [
                '|',
                ('state', 'not in', ['draft', 'cancel']),
                '&',
                ('state', '=', 'draft'),
                ('kanban_state', '=', 'done')
            ]
        domain = AND([contract_states, [
            ('employee_id', '=', self.employee_id.id),
            ('date_start', '<=', self.date_to),
            '|',
                ('date_end', '>=', self.date_from),
                ('date_end', '=', False),
        ]])
        return self.env['hr.contract'].sudo().search(domain)

    @api.constrains('date_from', 'date_to')
    def _check_contracts(self):
        """
            A leave cannot be set across multiple contracts.
            Note: a leave can be across multiple contracts despite this constraint.
            It happens if a leave is correctly created (not across multiple contracts) but
            contracts are later modifed/created in the middle of the leave.
        """
        for holiday in self.filtered('employee_id'):
            contracts = holiday._get_overlapping_contracts()
            if len(contracts.resource_calendar_id) > 1:
                state_labels = {e[0]: e[1] for e in contracts._fields['state']._description_selection(self.env)}
                raise ValidationError(
                    _("""A leave cannot be set across multiple contracts with different working schedules.

Please create one time off for each contract.

Time off:
%(time_off)s

Contracts:
%(contracts)s""",
                      time_off=holiday.display_name,
                      contracts='\n'.join(_(
                          "Contract %(contract)s from %(start_date)s to %(end_date)s, status: %(status)s",
                          contract=contract.name,
                          start_date=format_date(self.env, contract.date_start),
                          end_date=format_date(self.env, contract.date_end) if contract.date_end else _("undefined"),
                          status=state_labels[contract.state]
                      ) for contract in contracts)))
