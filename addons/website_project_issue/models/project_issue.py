# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, exceptions, models


class Issue(models.Model):
    _name = "project.issue"
    _inherit = ['project.issue']

    attachment_ids = fields.One2many('ir.attachment', compute='_compute_attachment_ids', string="Main Attachments",
                                     help="Attachment that don't come from message.")
    website_url = fields.Char('Website URL', compute='_compute_website_url', help='The full URL to access the document through the website.')

    def _compute_website_url(self):
        for issue in self:
            issue.website_url = '/my/issues/%s' % issue.id

    def _compute_attachment_ids(self):
        for issue in self:
            attachment_ids = self.env['ir.attachment'].search([('res_id', '=', issue.id), ('res_model', '=', 'project.issue')]).ids
            message_attachment_ids = self.mapped('message_ids.attachment_ids').ids # from mail_thread
            issue.attachment_ids = list(set(attachment_ids) - set(message_attachment_ids))

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
                    'url': self.website_url,
                    'target': 'self',
                    'res_id': self.id,
                }
        return super(Issue, self).get_access_action()

    @api.multi
    def _notification_recipients(self, message, groups):
        groups = super(Issue, self)._notification_recipients(message, groups)

        for group_name, group_method, group_data in groups:
            group_data['has_button_access'] = True

        return groups
