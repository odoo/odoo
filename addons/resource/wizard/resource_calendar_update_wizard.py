import ast

from odoo import api, fields, models


class ResourceCalendarUpdateWizard(models.TransientModel):
    _name = 'resource.calendar.update.wizard'
    _description = 'WS Update Confirmation'

    calendar_id = fields.Many2one('resource.calendar')
    new_vals = fields.Text() # Holds the stringified dictionary of changes
    employee_id = fields.Many2one('resource.resource') # Or hr.employee
    message = fields.Text(compute='_compute_message')


    @api.depends('calendar_id')
    def _compute_message(self):
        for wiz in self:
            wiz.message = _("This working schedule is linked to %s employees, are you sure you want to modify it for all employees?") % wiz.calendar_id.employees_count

    def action_update(self):
        """ Update the existing schedule for everyone """
        vals = ast.literal_eval(self.new_vals)
        # Use context to prevent infinite loop
        return self.calendar_id.with_context(skip_wizard=True).write(vals)

    def action_create_new(self):
        """ Copy the schedule and apply changes to the new one """
        vals = ast.literal_eval(self.new_vals)
        
        # 1. Create the new calendar as a copy of the old one (before changes)
        new_calendar = self.calendar_id.copy({
            'name': self.calendar_id.name + _(" (Individual)")
        })
        
        # 2. Apply the new changes to the copy
        new_calendar.with_context(skip_wizard=True).write(vals)
        
        # 3. If we know which employee we came from, link them
        if self.employee_id:
            self.employee_id.calendar_id = new_calendar.id
            
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'resource.calendar',
            'res_id': new_calendar.id,
            'view_mode': 'form',
            'target': 'current',
        }