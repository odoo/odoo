# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class Sponsor(models.Model):
    _name = 'event.sponsor'
    _inherit = ['event.sponsor']

    # contact information
    name = fields.Char('Sponsor Name', compute='_compute_name', readonly=False, store=True)
    email = fields.Char('Sponsor Email', compute='_compute_email', readonly=False, store=True)
    phone = fields.Char('Sponsor Phone', compute='_compute_phone', readonly=False, store=True)
    mobile = fields.Char('Sponsor Mobile', compute='_compute_mobile', readonly=False, store=True)
    # image
    image_512 = fields.Image(
        string="Logo", max_width=512, max_height=512,
        compute='_compute_image_512', readonly=False, store=True)
    image_256 = fields.Image("Image 256", related="image_512", max_width=256, max_height=256, store=False)
    image_128 = fields.Image("Image 128", related="image_512", max_width=128, max_height=128, store=False)

    @api.depends('partner_id')
    def _compute_name(self):
        self._synchronize_with_partner('name')

    @api.depends('partner_id')
    def _compute_email(self):
        self._synchronize_with_partner('email')

    @api.depends('partner_id')
    def _compute_phone(self):
        self._synchronize_with_partner('phone')

    @api.depends('partner_id')
    def _compute_mobile(self):
        self._synchronize_with_partner('mobile')

    @api.depends('partner_id')
    def _compute_image_512(self):
        self._synchronize_with_partner('image_512')

    def _synchronize_with_partner(self, fname):
        """ Synchronize with partner if not set. Setting a value does not write
        on partner as this may be event-specific information. """
        for sponsor in self:
            if not sponsor[fname]:
                sponsor[fname] = sponsor.partner_id[fname]
