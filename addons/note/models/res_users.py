# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


class Users(models.Model):

    _name = 'res.users'
    _inherit = ['res.users']

    @api.model
    def create(self, values):
        user = super(Users, self).create(values)
        # for new employee, create his own 5 base note stages
        if user.has_group('base.group_user'):
            for num in range(5):
                stage = self.env.ref('note.note_stage_%02d' % (num,), raise_if_not_found=False)
                if stage:
                    stage.sudo().copy(default={'user_id': user.id})
        return user

    @api.model
    def activity_user_count(self):
        """ If user created a note without activity, then by default it is not
            displayed in activity systray. So here making notes activity always
            visible even if notes not having activities. If there is no notes,
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
                    'icon': '/note/static/description/icon.png',
                    'total_count': 0,
                    'today_count': 0,
                    'overdue_count': 0,
                    'planned_count': 0
                })
        return activities
