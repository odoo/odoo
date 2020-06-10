# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class Lead(models.Model):
    _inherit = 'crm.lead'

    event_lead_rule_id = fields.Many2one('event.lead.rule', string="Registration Rule", help="Rule that created this lead")
    event_id = fields.Many2one('event.event', string="Source Event", help="Event triggering the rule that created this lead")
    registration_ids = fields.Many2many(
        'event.registration', string="Source Registrations",
        groups='event.group_event_user',
        help="Registrations triggering the rule that created this lead")
    registration_count = fields.Integer(
        string="# Registrations", compute='_compute_registration_count',
        groups='event.group_event_user',
        help="Counter for the registrations linked to this lead")

    @api.depends('registration_ids')
    def _compute_registration_count(self):
        for record in self:
            record.registration_count = len(record.registration_ids)
