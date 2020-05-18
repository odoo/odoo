# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Exhibitor(models.Model):
    _name = "event.exhibitor"
    _description = 'Event Exhibitor'
    _order = "sequence"
    _rec_name = 'partner_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    event_id = fields.Many2one('event.event', 'Event', required=True)
    create_jitsi_room = fields.Boolean('Create Jitsi Room',
        help="Automatically create a Jitsi room so that attendees can get in touch with the Exhibitor.")
    partner_id = fields.Many2one('res.partner', 'Exhibitor/Customer', required=True)
    partner_name = fields.Char('Name', related='partner_id.name')
    partner_email = fields.Char('Email', related='partner_id.email')
    partner_phone = fields.Char('Phone', related='partner_id.phone')
    partner_mobile = fields.Char('Mobile', related='partner_id.mobile')
    exhibitor_url = fields.Char('Exhibitor Website', compute='_compute_url', readonly=False, store=True)
    sequence = fields.Integer('Sequence')
    image_512 = fields.Image(
        string="Logo", related='partner_id.image_512', store=True, readonly=False)
    active = fields.Boolean(default=True)

    @api.depends('partner_id')
    def _compute_url(self):
        for exhibitor in self:
            exhibitor.exhibitor_url = exhibitor.partner_id.website

    def _message_get_suggested_recipients(self):
        recipients = super(Exhibitor, self)._message_get_suggested_recipients()
        for exhibitor in self:
            if exhibitor.partner_id:
                exhibitor._message_add_suggested_recipient(
                    recipients,
                    partner=exhibitor.partner_id,
                    reason=_('Exhibitor')
                )
        return recipients
