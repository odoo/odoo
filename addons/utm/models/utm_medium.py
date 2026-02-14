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

    @api.ondelete(at_uninstall=False)
    def _unlink_except_utm_medium_record(self):
        utm_medium_xml_ids = [
            key
            for key, (_label, model)
            in self.env['utm.mixin'].SELF_REQUIRED_UTM_REF.items()
            if model == 'utm.medium'
        ]

        for xml_id in utm_medium_xml_ids:
            utm_medium = self.env.ref(xml_id, raise_if_not_found=False)
            if utm_medium and utm_medium in self:
                raise UserError(_(
                    "Oops, you can't delete the Medium '%s'.\n"
                    "Doing so would be like tearing down a load-bearing wall \u2014 not the best idea.",
                    utm_medium.name
                ))
