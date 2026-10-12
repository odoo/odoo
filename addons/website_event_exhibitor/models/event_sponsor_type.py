# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventSponsorType(models.Model):
    _name = 'event.sponsor.type'
    _description = 'Event Sponsor Level'
    _order = "sequence"

    def _default_sequence(self):
        return (self.search([], order="sequence desc", limit=1).sequence or 0) + 1

    name = fields.Char('Sponsor Level', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=_default_sequence)
    display_ribbon_style = fields.Selection(
        [('no_ribbon', 'No Ribbon'), ('Gold', 'Gold'),
         ('Silver', 'Silver'), ('Bronze', 'Bronze')],
        string='Ribbon Style', default='no_ribbon')
