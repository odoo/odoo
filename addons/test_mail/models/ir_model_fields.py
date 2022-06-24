# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import mute_logger


class IrModelField(models.Model):
    _inherit = 'ir.model.fields'

    def _reflect_field_params(self, field, model_id):
        """ Disable the warnings for our specific test model. """
        if model_id == self.env['ir.model']._get_id('mail.test.track.compute'):
            with mute_logger('py.warnings'):
                return super(IrModelField, self)._reflect_field_params(field, model_id)
        else:
            return super(IrModelField, self)._reflect_field_params(field, model_id)
