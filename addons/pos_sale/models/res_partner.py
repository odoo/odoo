# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        data_fields = super()._load_pos_data_fields(config_id)
        data_fields += ['sale_warn', 'sale_warn_msg']
        return data_fields
