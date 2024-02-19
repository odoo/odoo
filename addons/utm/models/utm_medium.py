# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class UtmMedium(models.Model):
    _name = 'utm.medium'
    _description = 'UTM Medium'
    _order = 'name'

    name = fields.Char(string='Medium Name', required=True, translate=False)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'The name must be unique'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if name := vals.get('name'):
                vals['name'] = name.lower()
        try:
            return super().create(vals_list)
        except Exception as e:
            pattern = r"Key \(name\)=\((.*?)\)"
            match = re.search(pattern, str(e))
            raise ValidationError(f'The operation cannot be completed: The Medium "{match.group(1)}" already exists!')

    @api.ondelete(at_uninstall=False)
    def _unlink_except_utm_medium_email(self):
        utm_medium_email = self.env.ref('utm.utm_medium_email', raise_if_not_found=False)
        if utm_medium_email and utm_medium_email in self:
            raise UserError(_(
                "The UTM medium '%s' cannot be deleted as it is used in some main "
                "functional flows, such as the recruitment and the mass mailing.",
                utm_medium_email.name
            ))
