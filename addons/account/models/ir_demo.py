# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.modules.loading import force_demo
from odoo.addons.base.models.ir_module import assert_log_admin_access


class IrDemo(models.TransientModel):

    _inherit = 'ir.demo'
    _description = 'Demo override for demo data'

    @assert_log_admin_access
    def install_demo(self):
        original_company_country_code = self.env.company.country_code

        force_demo(self.env)

        if target_company := self.env['res.company'].search([('country_code', '=', original_company_country_code)], limit=1):
            return {
                'type': 'ir.actions.client',
                'tag': 'switch_company',
                'params': {
                    'company': target_company.id,
                },
            }
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': '/web',
        }
