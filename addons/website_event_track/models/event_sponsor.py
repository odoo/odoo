# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SponsorType(models.Model):
    _name = "event.sponsor.type"
    _description = 'Event Sponsor Type'
    _order = "sequence"

    name = fields.Char('Sponsor Type', required=True, translate=True)
    sequence = fields.Integer('Sequence')


class Sponsor(models.Model):
    _name = "event.sponsor"
    _description = 'Event Sponsor'
    _order = "sequence"

    event_id = fields.Many2one('event.event', 'Event', required=True)
    sponsor_type_id = fields.Many2one('event.sponsor.type', 'Sponsoring Type', required=True)
    partner_id = fields.Many2one('res.partner', 'Sponsor/Customer', required=True)
    url = fields.Char('Sponsor Website')
    sequence = fields.Integer('Sequence', store=True, related='sponsor_type_id.sequence', readonly=False)
    image_128 = fields.Image(string="Logo", related='partner_id.image_128', store=True, readonly=False)
