# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventSponsor(models.Model):
    _inherit = 'event.sponsor'

    booth_ids = fields.One2many('event.booth', 'sponsor_id', string='Booths')
