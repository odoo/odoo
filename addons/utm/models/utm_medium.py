# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, fields, models
from odoo.exceptions import UserError

import re


class UtmMedium(models.Model):
    _name = 'utm.medium'
    _description = 'UTM Medium'
    _order = 'name'

    name = fields.Char(string='Medium Name', required=True, translate=False)
    active = fields.Boolean(default=True)

    _unique_name = models.Constraint(
        'UNIQUE(name)',
        'The name must be unique',
    )

    @api.model_create_multi
    def create(self, vals_list):
        new_names = self.env['utm.mixin']._get_unique_names(self._name, [vals.get('name') for vals in vals_list])
        for vals, new_name in zip(vals_list, new_names):
            vals['name'] = new_name
        return super().create(vals_list)

    @property
    def SELF_REQUIRED_UTM_MEDIUMS_REF(self):
        return {
            'utm.utm_medium_email': 'Email',
            'utm.utm_medium_direct': 'Direct',
            'utm.utm_medium_website': 'Website',
            'utm.utm_medium_twitter': 'X',
            'utm.utm_medium_facebook': 'Facebook',
            'utm.utm_medium_linkedin': 'LinkedIn'
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_except_utm_medium_record(self):
        for medium in self.SELF_REQUIRED_UTM_MEDIUMS_REF:
            utm_medium = self.env.ref(medium, raise_if_not_found=False)
            if utm_medium and utm_medium in self:
                raise UserError(_(
                    "Oops, you can't delete the Medium '%s'.\n"
                    "Doing so would be like tearing down a load-bearing wall \u2014 not the best idea.",
                    utm_medium.name
                ))

    def _fetch_or_create_utm_medium(self, name, module='utm'):
        name_normalized = re.sub(r"[\s|.]", "_", name.lower())
        try:
            return self.env.ref(f'{module}.utm_medium_{name_normalized}')
        except ValueError:
            utm_medium = self.sudo().env['utm.medium'].create({
                'name': self.SELF_REQUIRED_UTM_MEDIUMS_REF.get(f'{module}.utm_medium_{name_normalized}', name)
            })
            self.sudo().env['ir.model.data'].create({
                'name': f'utm_medium_{name_normalized}',
                'module': module,
                'res_id': utm_medium.id,
                'model': 'utm.medium',
            })
            return utm_medium
