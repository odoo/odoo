# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MrpMarkdoneConfirmation(models.TransientModel):
    _name = 'mrp.markdone.confirmation'

    production_id = fields.Many2one('mrp.production')

    @api.multi
    def action_done(self):
        self.ensure_one()
        return self.production_id.action_done()
