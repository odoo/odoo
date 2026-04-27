# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def set_values(self):
        fsm_projects = self.env['project.project'].sudo().search([('is_fsm', '=', True)])
        if fsm_projects:
            fsm_projects.write({'allow_quotations': self.group_industry_fsm_quotations})
        return super().set_values()
