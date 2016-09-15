# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, models

class Project(models.Model):
    _inherit = ['project.project']

    @api.multi
    def get_access_action(self):
        """ Instead of the classic form view, redirect to website for portal users
        that can read the project. """
        self.ensure_one()
        if self.env.user.share:
            try:
                self.check_access_rule('read')
            except exceptions.AccessError:
                pass
            else:
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/my/project/%s' % self.id,
                    'target': 'self',
                    'res_id': self.id,
                }
        return super(Project, self).get_access_action()

    @api.multi
    def _notification_group_recipients(self, message, recipients, done_ids, group_data):
        """ Override the method to place the portal customers in the 'user' group data as a portal view now exists"""
        for recipient in recipients:
            if recipient.id in done_ids:
                continue
            if recipient.user_ids and all(recipient.user_ids.mapped('share')):
                group_data['user'] |= recipient
                done_ids.add(recipient.id)
        return super(Project, self)._notification_group_recipients(message, recipients, done_ids, group_data)


class Task(models.Model):
    _inherit = ['project.task']

    @api.multi
    def get_access_action(self):
        """ Instead of the classic form view, redirect to website for portal users
        that can read the task. """
        self.ensure_one()
        if self.env.user.share:
            try:
                self.check_access_rule('read')
            except exceptions.AccessError:
                pass
            else:
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/my/task/%s' % self.id,
                    'target': 'self',
                    'res_id': self.id,
                }
        return super(Task, self).get_access_action()

    @api.multi
    def _notification_group_recipients(self, message, recipients, done_ids, group_data):
        """ Override the method to place the portal customers in the 'user' group data as a portal view now exists"""
        for recipient in recipients:
            if recipient.id in done_ids:
                continue
            if recipient.user_ids and all(recipient.user_ids.mapped('share')):
                group_data['user'] |= recipient
                done_ids.add(recipient.id)
        return super(Task, self)._notification_group_recipients(message, recipients, done_ids, group_data)
