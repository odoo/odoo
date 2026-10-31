# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import fields, models, _


class EventBooth(models.Model):
    _inherit = 'event.booth'

    use_sponsor = fields.Boolean(related='booth_category_id.use_sponsor')
    sponsor_type_id = fields.Many2one(related='booth_category_id.sponsor_type_id')
    sponsor_id = fields.Many2one('event.sponsor', string='Sponsor', copy=False, index='btree_not_null')
    sponsor_name = fields.Char(string='Sponsor Name', related='sponsor_id.name')
    sponsor_email = fields.Char(string='Sponsor Email', related='sponsor_id.email')
    sponsor_phone = fields.Char(string='Sponsor Phone', related='sponsor_id.phone')
    sponsor_subtitle = fields.Char(string='Sponsor Slogan', related='sponsor_id.subtitle')
    sponsor_website_description = fields.Html(string='Sponsor Description', related='sponsor_id.website_description')
    sponsor_image_512 = fields.Image(string='Sponsor Logo', related='sponsor_id.image_512')

    def write(self, vals):
        released_sponsors = []
        if vals.get('state') == 'available':
            # '_get_release_values' drops the sponsor link, so it is read before
            # the booths are freed to still be notified afterwards.
            # sudo: event.booth - booths can be released by the event user, and they don't have access to sponsors.
            released_sponsors = [
                (booth.display_name, booth.sponsor_id)
                for booth in self.sudo().filtered(
                    lambda booth: booth.state == 'unavailable' and booth.sponsor_id)
            ]
        res = super().write(vals)
        for booth_name, sponsor in released_sponsors:
            sponsor.message_post(body=Markup('<p>%s</p>') % _(
                'Booth %(booth_name)s has been released and is not linked to this sponsor anymore.',
                booth_name=booth_name))
        return res

    def action_view_sponsor(self):
        action = self.env['ir.actions.act_window']._for_xml_id('website_event_exhibitor.event_sponsor_action')
        action['views'] = [(False, 'form')]
        action['res_id'] = self.sponsor_id.id
        return action

    def _get_or_create_sponsor(self, vals):
        self.ensure_one()
        sponsor_id = self.env['event.sponsor'].sudo().search([
            ('partner_id', '=', self.partner_id.id),
            ('sponsor_type_id', '=', self.sponsor_type_id.id),
            ('exhibitor_type', '=', self.booth_category_id.exhibitor_type),
            ('event_id', '=', self.event_id.id),
        ], limit=1)
        if not sponsor_id:
            values = {
                'event_id': self.event_id.id,
                'sponsor_type_id': self.sponsor_type_id.id,
                'exhibitor_type': self.booth_category_id.exhibitor_type,
                'partner_id': self.partner_id.id,
                **{key.partition('sponsor_')[2]: value for key, value in vals.items() if key.startswith('sponsor_')},
            }
            # If confirmed from backend, we don't have _prepare_booth_registration_values
            if not values.get('name'):
                values['name'] = self.partner_id.name
            sponsor_id = self.env['event.sponsor'].sudo().create(values)
        return sponsor_id.id

    def _action_post_confirm(self, write_vals):
        for booth in self:
            if booth.use_sponsor and booth.partner_id:
                booth.sponsor_id = booth._get_or_create_sponsor(write_vals)
        super(EventBooth, self)._action_post_confirm(write_vals)

    def _get_release_values(self):
        return {**super()._get_release_values(), 'sponsor_id': False}
