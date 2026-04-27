# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class IrModelData(models.Model):
    _inherit = 'ir.model.data'

    studio = fields.Boolean(help='Checked if it has been edited with Studio.')

    @api.model_create_multi
    def create(self, vals_list):
        if self._context.get('studio'):
            for vals in vals_list:
                vals['studio'] = True
        return super().create(vals_list)

    def write(self, vals):
        """ When editing an ir.model.data with Studio, we put it in noupdate to
                avoid the customizations to be dropped when upgrading the module.
        """
        if self._context.get('studio'):
            vals['noupdate'] = True
            vals['studio'] = True
        return super(IrModelData, self).write(vals)

    def _build_insert_xmlids_values(self):
        values = super()._build_insert_xmlids_values()
        if self._context.get('studio'):
            values['studio'] = 'true'
        return values

    def _xmlid_for_export(self):
        self.ensure_one()
        return self.complete_name.replace('__export__.', '').replace('studio_customization.', '')
