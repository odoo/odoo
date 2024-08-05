# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import _, models


class HrDepartureWizard(models.TransientModel):
    _inherit = 'hr.departure.wizard'

    def action_register_departure(self):
        super(HrDepartureWizard, self).action_register_departure()
<<<<<<< saas-17.1
        employee_leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_to', '>', self.departure_date),
            ('state', '!=', 'refuse')
        ])
        to_delete = self.env['hr.leave']
        to_cancel = self.env['hr.leave']
        for leave in employee_leaves:
            if leave.state == 'validate':
                to_cancel |= leave
            else:
                to_delete |= leave
        to_delete.unlink()
        to_cancel._force_cancel(_('The employee no longer works in the company'), notify_responsibles=False)
||||||| be261aab2659305033d24ef1b3e631cd43f250b7
        if self.cancel_leaves:
            future_leaves = self.env['hr.leave'].search([('employee_id', '=', self.employee_id.id), 
                                                         ('date_to', '>', self.departure_date),
                                                         ('state', '!=', 'refuse')])
            future_leaves.write({'state': 'refuse'})
=======
        if self.cancel_leaves:
            future_leaves = self.env['hr.leave'].search([('employee_id', '=', self.employee_id.id), 
                                                         ('date_to', '>', self.departure_date),
                                                         ('state', '!=', 'refuse')])
            future_leaves.action_refuse()
>>>>>>> 8f3714eeaec9cb48414a1cfe9516b2554151ec8b

        employee_allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', self.employee_id.id),
            '|',
                ('date_to', '=', False),
                ('date_to', '>', self.departure_date),
        ])
        to_delete = self.env['hr.leave.allocation']
        to_modify = self.env['hr.leave.allocation']
        for allocation in employee_allocations:
            if allocation.date_from > self.departure_date:
                to_delete |= allocation
            else:
                to_modify |= allocation
                allocation.message_post(
                    body=_('Validity End date has been updated because Employee no longer works in the company'),
                    subtype_xmlid='mail.mt_comment'
                )
        to_delete.write({'state': 'confirm'}) # Needs to be confirmed before it can be unlinked
        to_delete.unlink()
        to_modify.date_to = self.departure_date
