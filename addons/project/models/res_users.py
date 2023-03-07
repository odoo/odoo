# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, modules


class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    @api.model
    def systray_get_activities(self):
        """ Change the icon of activity related to project.task the the one of the Project app
            TO-DO: This method override will change after the refactor of discuss app to separate
            private tasks from tasks belonging to project in the activity notifications. The first
            one will direct to the to-do app.
        """
        activities = super(Users, self).systray_get_activities()
        tasks_count = self.env['project.task'].sudo().search_count([('user_ids', 'in', [self.env.uid])])
        if tasks_count:
            task_index = next((index for (index, a) in enumerate(activities) if a["model"] == "project.task"), None)
            task_label = _("Task")
            if task_index is not None:
                activities[task_index]['icon'] = modules.module.get_module_icon(self.env['project.project']._original_module)
                activities[task_index]['name'] = task_label
        return activities
