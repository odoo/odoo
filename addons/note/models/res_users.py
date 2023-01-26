# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, modules, _, _lt

class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    @api.model
    def systray_get_activities(self):
        """ If user have not scheduled any note, it will not appear in activity menu.
            Making note activity always visible with number of notes on label. If there is no notes,
            activity menu not visible for note.
        """
        activities = super(Users, self).systray_get_activities()
        notes_count = self.env['project.task'].sudo().search_count([('user_ids', 'in', [self.env.uid])])
        if notes_count:
            note_index = next((index for (index, a) in enumerate(activities) if a["model"] == "project.task"), None)
            note_label = _("To-do")
            if note_index is not None:
                activities[note_index]['name'] = note_label
            else:
                activities.append({
                    'id': self.env['ir.model']._get('project.task').id,
                    'type': 'activity',
                    'name': note_label,
                    'model': 'project.task',
                    'icon': modules.module.get_module_icon(self.env['project.task']._original_module),
                    'total_count': 0,
                    'today_count': 0,
                    'overdue_count': 0,
                    'planned_count': 0
                })
        return activities
