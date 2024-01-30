# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('key') in ['mail.bounce.alias', 'mail.catchall.alias']:
                vals['value'] = self.env['mail.alias']._clean_and_check_unique([vals.get('value')])[0]
        return super().create(vals_list)

    def write(self, vals):
        for parameter in self:
            if 'value' in vals and parameter.key in ['mail.bounce.alias', 'mail.catchall.alias'] and vals['value'] != parameter.value:
                vals['value'] = self.env['mail.alias']._clean_and_check_unique([vals.get('value')])[0]
        return super().write(vals)

    @api.model
    def set_param(self, key, value):
        if key == 'mail.restrict.template.rendering':
            group_user = self.env.ref('base.group_user')
            group_mail_template_editor = self.env.ref('mail.group_mail_template_editor')

            if not value and group_mail_template_editor not in group_user.implied_ids:
                group_user.implied_ids |= group_mail_template_editor

            elif value and group_mail_template_editor in group_user.implied_ids:
                # remove existing users, including inactive template user
                # admin will regain the right via implied_ids on group_system
                group_user._remove_group(group_mail_template_editor)
        # sanitize and normalize allowed catchall domains
        elif key == 'mail.catchall.domain.allowed' and value:
            value = self.env['mail.alias']._clean_and_check_mail_catchall_allowed_domains(value)

        return super(IrConfigParameter, self).set_param(key, value)
