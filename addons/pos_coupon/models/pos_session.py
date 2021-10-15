# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv.expression import OR


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        if self.config_id.use_coupon_programs and len(self.config_id.program_ids) > 0:
            new_model = 'coupon.program'
            if new_model not in result:
                result.append(new_model)
        return result

    def _loader_params_coupon_program(self):
        return {
            'search_params': {
                'domain': [('id', 'in', self.config_id.program_ids.ids), ('active', '=', True)],
                'fields': []
            },
        }

    def _get_pos_ui_coupon_program(self, params):
        return self.env['coupon.program'].search_read(**params['search_params'])

    def _loader_params_product_product(self):
        result = super(PosSession, self)._loader_params_product_product()
        if self.config_id.use_coupon_programs and len(self.config_id.program_ids) > 0:
            discount_product_ids = self.config_id.program_ids.mapped(lambda program: program.discount_line_product_id.id)
            reward_product_ids = self.config_id.program_ids.mapped(lambda program: program.reward_product_id.id)
            product_ids = [id for id in [*discount_product_ids, *reward_product_ids] if id]
            result['search_params']['domain'] = OR([result['search_params']['domain'], [('id', 'in', product_ids)]])
        return result
