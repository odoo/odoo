# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models


_logger = logging.getLogger(__name__)

class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    def write(self, vals):
        result = super(IrConfigParameter, self).write(vals)
        if vals.get('key') == "crm.pls_fields":
            self.flush()
            self.env.registry.setup_models(self.env.cr)
            _logger.warning("setup_models")
        return result

    @api.model_create_multi
    def create(self, vals_list):
        results = super(IrConfigParameter, self).create(vals_list)
        setup_models = False
        for vals in vals_list:
            if vals['key'] == "crm.pls_fields":
                setup_models = True
        if setup_models:
            self.flush()
            self.env.registry.setup_models(self.env.cr)
            _logger.warning("setup_models")
        return results

    def set_param(self, key, value):
        result = super(IrConfigParameter, self).set_param(key, value)
        if key == "crm.pls_fields":
            self.flush()
            self.env.registry.setup_models(self.env.cr)
            _logger.warning("setup_models")
        return result
