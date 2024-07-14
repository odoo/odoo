# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HelpdeskTicketCreateTimesheet(models.TransientModel):
    _name = 'helpdesk.ticket.create.timesheet'
    _description = "Create Timesheet from ticket"

    time_spent = fields.Float('Time')
    description = fields.Char('Description')
    ticket_id = fields.Many2one(
        'helpdesk.ticket', "Ticket", required=True,
        default=lambda self: self.env.context.get('active_id', None),
        help="Ticket for which we are creating a sales order",
    )

    def action_generate_timesheet(self):
        values = {
            'project_id': self.ticket_id.project_id.id,
            'name': self.description,
            'user_id': self.env.uid,
            'unit_amount': self.time_spent,
        }

        timesheet = self.env['account.analytic.line'].create(values)

        self.ticket_id.write({
            'timer_start': False,
            'timer_pause': False
        })
        self.ticket_id.timesheet_ids = [(4, timesheet.id, None)]
        self.ticket_id.user_timer_id.unlink()
        return timesheet

    def action_delete_timesheet(self):
         self.ticket_id.user_timer_id.unlink()
