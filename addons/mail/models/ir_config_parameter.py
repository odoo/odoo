# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('key') in ['mail.bounce.alias', 'mail.catchall.alias']:
                vals['value'] = self.env['mail.alias']._clean_and_check_unique(vals.get('value'))
            elif vals.get('key') == 'mail.catchall.domain.allowed':
                vals['value'] = vals.get('value') and self._clean_and_check_mail_catchall_allowed_domains(vals['value'])
        return super().create(vals_list)

    def write(self, vals):
        for parameter in self:
            if 'value' in vals and parameter.key in ['mail.bounce.alias', 'mail.catchall.alias'] and vals['value'] != parameter.value:
                vals['value'] = self.env['mail.alias']._clean_and_check_unique(vals.get('value'))
            elif 'value' in vals and parameter.key == 'mail.catchall.domain.allowed' and vals['value'] != parameter.value:
                vals['value'] = vals['value'] and self._clean_and_check_mail_catchall_allowed_domains(vals['value'])
        return super().write(vals)

    def _clean_and_check_mail_catchall_allowed_domains(self, value):
        """ The purpose of this system parameter is to avoid the creation
        of records from incoming emails with a domain != alias_domain
        but that have a pattern matching an internal mail.alias . """
        value = [domain.strip().lower() for domain in value.split(',') if domain.strip()]
        if not value:
            raise ValidationError(_("Value for `mail.catchall.domain.allowed` cannot be validated.\n"
                                    "It should be a comma separated list of domains e.g. example.com,example.org."))
        return ",".join(value)
