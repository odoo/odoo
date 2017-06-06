# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, models, fields
from odoo.addons.website.models.website import slug


class Project(models.Model):
    _inherit = ['project.project']

    @api.multi
    def get_access_action(self, access_uid=None):
        """ Instead of the classic form view, redirect to website for portal users
        that can read the project. """
        self.ensure_one()
        user, record = self.env.user, self
        if access_uid:
            user = self.env['res.users'].sudo().browse(access_uid)
            record = self.sudo(user)

        if user.share:
            try:
                record.check_access_rule('read')
            except exceptions.AccessError:
                pass
            else:
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/my/project/%s' % self.id,
                    'target': 'self',
                    'res_id': self.id,
                }
        return super(Project, self).get_access_action(access_uid)

    @api.multi
    def _notification_recipients(self, message, groups):
        groups = super(Project, self)._notification_recipients(message, groups)

        for group_name, group_method, group_data in groups:
            group_data['has_button_access'] = True

        return groups


class Task(models.Model):
    _inherit = ['project.task']

    website_url = fields.Char('Website URL', compute='_compute_website_url', help='The full URL to access the document through the website.')

    attachment_ids = fields.One2many('ir.attachment', compute='_compute_attachment_ids', string="Main Attachments",
                                     help="Attachment that don't come from message.")

    def _compute_attachment_ids(self):
        for task in self:
            attachment_ids = self.env['ir.attachment'].search([('res_id', '=', task.id), ('res_model', '=', 'project.task')]).ids
            message_attachment_ids = self.mapped('message_ids.attachment_ids').ids  # from mail_thread
            task.attachment_ids = list(set(attachment_ids) - set(message_attachment_ids))

    def _compute_website_url(self):
        for task in self:
            task.website_url = '/my/task/%s' % task.id

    @api.multi
    def get_access_action(self, access_uid=None):
        """ Instead of the classic form view, redirect to website for portal users
        that can read the task. """
        self.ensure_one()
        user, record = self.env.user, self
        if access_uid:
            user = self.env['res.users'].sudo().browse(access_uid)
            record = self.sudo(user)

        if user.share:
            try:
                record.check_access_rule('read')
            except exceptions.AccessError:
                pass
            else:
                return {
                    'type': 'ir.actions.act_url',
                    'url': self.website_url,
                    'target': 'self',
                    'res_id': self.id,
                }
        return super(Task, self).get_access_action(access_uid)

    @api.multi
    def _notification_recipients(self, message, groups):
        groups = super(Task, self)._notification_recipients(message, groups)

        for group_name, group_method, group_data in groups:
            group_data['has_button_access'] = True

        return groups
