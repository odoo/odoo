# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, modules, _


class Users(models.Model):

    _name = 'res.users'
    _inherit = ['res.users']

    @api.model
    def create(self, values):
        user = super(Users, self).create(values)
        # for new employee, create his own 5 base note stages
        if user.has_group('base.group_user'):
            for num in range(4):
                stage = self.env.ref('note.note_stage_%02d' % (num,), raise_if_not_found=False)
                if stage:
                    stage.sudo().copy(default={'user_id': user.id})
        return user

    @api.model
    def activity_user_count(self):
        """ If user have not scheduled any note, it will not appear in activity menu.
            Making note activity always visible with number of notes on label. If there is no notes,
            activity menu not visible for note.
        """
        activities = super(Users, self).activity_user_count()
        notes_count = self.env['note.note'].search_count([('user_id', '=', self.env.uid), ('open', '=', True)])
        if notes_count:
            note_index = next((index for (index, a) in enumerate(activities) if a["model"] == "note.note"), None)
            note_label = ("%s (%d)") % (_('Notes'), notes_count)
            if note_index is not None:
                activities[note_index]['name'] = note_label
            else:
                activities.append({
                    'name': note_label,
                    'model': 'note.note',
                    'icon': modules.module.get_module_icon(self.env['note.note']._original_module),
                    'total_count': 0,
                    'today_count': 0,
                    'overdue_count': 0,
                    'planned_count': 0
                })
        return activities
