# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, models


class Issue(models.Model):
    _name = "project.issue"
    _inherit = ['project.issue']

    @api.multi
    def get_access_action(self):
        """ Instead of the classic form view, redirect to website for portal users
        that can read the issue. """
        self.ensure_one()
        if self.env.user.share:
            try:
                self.check_access_rule('read')
            except exceptions.AccessError:
                pass
            else:
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/my/issues/%s' % self.id,
                    'target': 'self',
                    'res_id': self.id,
                }
        return super(Issue, self).get_access_action()

    @api.multi
    def _notification_group_recipients(self, message, recipients, done_ids, group_data):
        """ Override the mail.thread method to handle project users and officers
        recipients. Indeed those will have specific action in their notification
        emails: creating tasks, assigning it. """
        group_project_user_id = self.env.ref('project.group_project_user').id
        for recipient in recipients:
            if recipient.id in done_ids:
                continue
            if recipient.user_ids and group_project_user_id in recipient.user_ids[0].groups_id.ids:
                group_data['group_project_user'] |= recipient
                done_ids.add(recipient.id)
            elif recipient.user_ids and all(recipient.user_ids.mapped('share')):
                group_data['user'] |= recipient
                done_ids.add(recipient.id)
        return super(Issue, self)._notification_group_recipients(message, recipients, done_ids, group_data)
