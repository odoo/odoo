# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SponsorType(models.Model):
    _name = "event.sponsor.type"
    _description = 'Event Sponsor Type'
    _order = "sequence"

    name = fields.Char('Sponsor Type', required=True, translate=True)
    sequence = fields.Integer('Sequence')


class Sponsor(models.Model):
    _name = "event.sponsor"
    _description = 'Event Sponsor'
    _order = "sequence, sponsor_type_id"
    _rec_name = 'partner_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    event_id = fields.Many2one('event.event', 'Event', required=True)
    sponsor_type_id = fields.Many2one('event.sponsor.type', 'Sponsoring Type', required=True)
    partner_id = fields.Many2one('res.partner', 'Sponsor/Customer', required=True)
    partner_name = fields.Char('Name', related='partner_id.name')
    partner_email = fields.Char('Email', related='partner_id.email')
    partner_phone = fields.Char('Phone', related='partner_id.phone')
    partner_mobile = fields.Char('Mobile', related='partner_id.mobile')
    url = fields.Char('Sponsor Website', compute='_compute_url', readonly=False, store=True)
    sequence = fields.Integer('Sequence')
    image_128 = fields.Image(
        string="Logo", related='partner_id.image_128', store=True, readonly=False)
    active = fields.Boolean(default=True)

    @api.depends('partner_id')
    def _compute_url(self):
        for sponsor in self:
            sponsor.url = sponsor.partner_id.website

    def _message_get_suggested_recipients(self):
        recipients = super(Sponsor, self)._message_get_suggested_recipients()
        for sponsor in self:
            if sponsor.partner_id:
                sponsor._message_add_suggested_recipient(
                    recipients,
                    partner=sponsor.partner_id,
                    reason=_('Sponsor')
                )
        return recipients
