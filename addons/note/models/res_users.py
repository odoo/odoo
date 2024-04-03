# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models, modules, _

_logger = logging.getLogger(__name__)


class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        user_group_id = self.env['ir.model.data']._xmlid_to_res_id('base.group_user')
        # for new employee, create his own 5 base note stages
        users.filtered_domain([('groups_id', 'in', [user_group_id])])._create_note_stages()
        return users

    @api.model
    def _init_data_user_note_stages(self):
        emp_group_id = self.env.ref('base.group_user').id
        query = """
SELECT res_users.id
FROM res_users
WHERE res_users.active IS TRUE AND EXISTS (
    SELECT 1 FROM res_groups_users_rel WHERE res_groups_users_rel.gid = %s AND res_groups_users_rel.uid = res_users.id
) AND NOT EXISTS (
    SELECT 1 FROM note_stage stage WHERE stage.user_id = res_users.id
)
GROUP BY id"""
        self.env.cr.execute(query, (emp_group_id,))
        uids = [res[0] for res in self.env.cr.fetchall()]
        self.browse(uids)._create_note_stages()

    def _create_note_stages(self):
        for num in range(4):
            stage = self.env.ref('note.note_stage_%02d' % (num,), raise_if_not_found=False)
            if not stage:
                break
            for user in self:
                stage.sudo().copy(default={'user_id': user.id})
        else:
            _logger.debug("Created note columns for %s", self)

    @api.model
    def systray_get_activities(self):
        """ If user have not scheduled any note, it will not appear in activity menu.
            Making note activity always visible with number of notes on label. If there is no notes,
            activity menu not visible for note.
        """
        activities = super(Users, self).systray_get_activities()
        notes_count = self.env['note.note'].search_count([('user_id', '=', self.env.uid)])
        if notes_count:
            note_index = next((index for (index, a) in enumerate(activities) if a["model"] == "note.note"), None)
            note_label = _('Notes')
            if note_index is not None:
                activities[note_index]['name'] = note_label
            else:
                activities.append({
                    'id': self.env['ir.model']._get('note.note').id,
                    'type': 'activity',
                    'name': note_label,
                    'model': 'note.note',
                    'icon': modules.module.get_module_icon(self.env['note.note']._original_module),
                    'total_count': 0,
                    'today_count': 0,
                    'overdue_count': 0,
                    'planned_count': 0
                })
        return activities
