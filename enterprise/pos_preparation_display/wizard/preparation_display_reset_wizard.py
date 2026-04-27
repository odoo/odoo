# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosPreparationDisplayResetWizard(models.TransientModel):
    _name = 'pos_preparation_display.reset.wizard'
    _description = 'Reset all current order in a preparation display'

    def reset_all_orders(self):
        preparation_display = self.env['pos_preparation_display.display'].search([('id', '=', self.env.context['preparation_display_id'])])
        preparation_display.reset()
