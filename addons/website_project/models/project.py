# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, models, fields
from odoo.addons.website.models.website import slug


class Project(models.Model):
    _inherit = ['project.project']

    # DO NOT FORWARD-PORT (only for saas-15)
    website_url = fields.Char('Website URL', compute='_compute_website_url', help='The full URL to access the document through the website.')

    def _compute_website_url(self):
        for project in self:
            project.website_url = '/my/project/%s' % project.id

    @api.multi
    def get_access_action(self):
        """ Instead of the classic form view, redirect to website for portal users
        that can read the project. """
        self.ensure_one()
        if self.env.context.get('uid'):
            user = self.env['res.users'].browse(self.env.context['uid'])
        else:
            user = self.env.user
        if user.share:
            try:
                self.check_access_rule('read')
            except exceptions.AccessError:
                pass
            else:
                return {
                    'type': 'ir.actions.act_url',
                    'url': self.website_url,
                    'target': 'self',
                    'res_id': self.id,
                }
        return super(Project, self).get_access_action()

    @api.multi
    def _notification_recipients(self, message, groups):
        groups = super(Project, self)._notification_recipients(message, groups)

        for group_name, group_method, group_data in groups:
            group_data['has_button_access'] = True

        return groups


class Task(models.Model):
    _inherit = ['project.task']

    website_url = fields.Char('Website URL', compute='_compute_website_url', help='The full URL to access the document through the website.')

    def _compute_website_url(self):
        for task in self:
            task.website_url = '/my/task/%s' % task.id

    @api.multi
    def get_access_action(self):
        """ Instead of the classic form view, redirect to website for portal users
        that can read the task. """
        self.ensure_one()
        if self.env.context.get('uid'):
            user = self.env['res.users'].browse(self.env.context['uid'])
        else:
            user = self.env.user
        if user.share:
            try:
                self.check_access_rule('read')
            except exceptions.AccessError:
                pass
            else:
                return {
                    'type': 'ir.actions.act_url',
                    'url': self.website_url,
                    'target': 'self',
                    'res_id': self.id,
                }
        return super(Task, self).get_access_action()

    @api.multi
    def _notification_recipients(self, message, groups):
        groups = super(Task, self)._notification_recipients(message, groups)

        for group_name, group_method, group_data in groups:
            group_data['has_button_access'] = True

        return groups
