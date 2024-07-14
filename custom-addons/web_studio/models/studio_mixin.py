# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class StudioMixin(models.AbstractModel):
    """ Mixin that overrides the create and write methods to properly generate
        ir.model.data entries flagged with Studio for the corresponding resources.
        Doesn't create an ir.model.data if the record is part of a module being
        currently installed as the ir.model.data will be created automatically
        afterwards.
    """
    _name = 'studio.mixin'
    _description = 'Studio Mixin'

    @api.model_create_multi
    def create(self, vals):
        res = super(StudioMixin, self).create(vals)
        if self._context.get('studio') and not self._context.get('install_mode'):
            res._compute_display_name()
            for ob in res:
                ob.create_studio_model_data(ob.display_name)
        return res

    def write(self, vals):
        if 'display_name' in vals and len(vals) == 1 and not self.env.registry[self._name].display_name.base_field.store:
            # the call _compute_display_name() above performs an unexpected call
            # to write with 'display_name', which triggers a costly registry
            # setup when applied on ir.model or ir.model.fields.
            return

        res = super(StudioMixin, self).write(vals)

        if self._context.get('studio') and not self._context.get('install_mode'):
            for record in self:
                record.create_studio_model_data(record.display_name)

        return res
