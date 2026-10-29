# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def open_followup_level_form(self):
        res_ids = self.env['followup.followup'].search([], limit=1)
        return {
            'type': 'ir.actions.act_window',
            'name': 'Follow-up Levels',
            'res_model': 'followup.followup',
            'res_id': res_ids and res_ids.id or False,
            'view_mode': 'form,tree',
        }
