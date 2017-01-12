# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, exceptions, models, _


class Issue(models.Model):
    _name = "project.issue"
    _inherit = ['project.issue']

    main_attachment_ids =  fields.One2many('ir.attachment', compute='_compute_attachment_ids', string="Main Attachments",
                                           help="Attachment that don't come from message.")
    def _compute_attachment_ids(self):
        for issue in self:
            all_attach = self.env['ir.attachment'].search([('res_id', '=', issue.id), ('res_model', '=', 'project.issue')]).ids
            message_attach_ids = []
            for m in self.mapped('message_ids'):
                message_attach_ids += m.attachment_ids.ids
            issue.main_attachment_ids = list(set(all_attach) - set(message_attach_ids))

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
    def _notification_recipients(self, message, groups):
        groups = super(Issue, self)._notification_recipients(message, groups)

        for group_name, group_method, group_data in groups:
            group_data['has_button_access'] = True

        return groups
