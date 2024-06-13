# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, fields, models
from odoo.exceptions import UserError


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
        new_names = self.env['utm.mixin']._get_unique_names(self._name, [vals.get('name') for vals in vals_list])
        for vals, new_name in zip(vals_list, new_names):
            vals['name'] = new_name
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_utm_medium_email(self):
        utm_medium_email = self.env.ref('utm.utm_medium_email', raise_if_not_found=False)
        if utm_medium_email and utm_medium_email in self:
            raise UserError(_(
                "The UTM medium '%s' cannot be deleted as it is used in some main "
                "functional flows, such as the recruitment and the mass mailing.",
                utm_medium_email.name
            ))
