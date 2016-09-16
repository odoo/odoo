# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, models, _


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
    def _notification_recipients(self, message, groups):
        groups = super(Issue, self)._notification_recipients(message, groups)

        for group_name, group_method, group_data in groups:
            group_data['has_button_access'] = True

        return groups
