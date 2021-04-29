# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventBooth(models.Model):
    _inherit = 'event.booth'

    use_sponsor = fields.Boolean(related='booth_category_id.use_sponsor')
    sponsor_type_id = fields.Many2one(related='booth_category_id.sponsor_type_id')
    sponsor_id = fields.Many2one(
        'event.sponsor', string='Sponsor')

    def write(self, vals):
        # TODO: This will create a new sponsor for each booth event when a user register for several booths
        for booth in self:
            if booth.use_sponsor and not vals.get('sponsor_id'):
                vals['sponsor_id'] = booth._get_sponsor(vals)
        return super(EventBooth, self).write(vals)

    def action_view_sponsor(self):
        action = self.env['ir.actions.act_window']._for_xml_id('website_event_exhibitor.event_sponsor_action')
        action['views'] = [(False, 'form')]
        action['res_id'] = self.sponsor_id.id
        return action

    def _get_sponsor(self, vals):
        self.ensure_one()
        sponsor_id = self.env['event.sponsor'].sudo().search([
            ('partner_id', '=', vals.get('partner_id')),
            ('event_id', '=', self.event_id.id),
        ], limit=1)
        if sponsor_id:
            return sponsor_id.id
        values = {
            'event_id': vals.get('event_id') or self.event_id.id,
            'sponsor_type_id': self.sponsor_type_id.id,
            'exhibitor_type': self.booth_category_id.exhibitor_type,
            'partner_id': vals.get('partner_id'),
        }
        return self.env['event.sponsor'].sudo().create(values)
