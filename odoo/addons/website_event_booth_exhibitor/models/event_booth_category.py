# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventBoothCategory(models.Model):
    _inherit = 'event.booth.category'

    @api.model
    def _get_exhibitor_type(self):
        return self.env['event.sponsor']._fields['exhibitor_type'].selection

    use_sponsor = fields.Boolean(string='Create Sponsor', help="If set, when booking a booth a sponsor will be created for the user")
    sponsor_type_id = fields.Many2one('event.sponsor.type', string='Sponsor Level')
    exhibitor_type = fields.Selection(_get_exhibitor_type, string='Sponsor Type')

    @api.onchange('use_sponsor')
    def _onchange_use_sponsor(self):
        if self.use_sponsor:
            if not self.sponsor_type_id:
                self.sponsor_type_id = self.env['event.sponsor.type'].search([], order="sequence desc", limit=1).id
            if not self.exhibitor_type:
                self.exhibitor_type = self._get_exhibitor_type()[0][0]
