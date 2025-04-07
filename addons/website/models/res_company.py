# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Company(models.Model):
    _inherit = "res.company"

    website_id = fields.Many2one('website', compute='_compute_website_id', store=True)

    def _compute_website_id(self):
        for company in self:
            company.website_id = self.env['website'].search([('company_id', '=', company.id)], limit=1)

    @api.model
    def action_open_website_theme_selector(self):
        action = self.env["ir.actions.actions"]._for_xml_id("website.theme_install_kanban_action")
        action['target'] = 'new'
        return action

    @api.constrains('active')
    def _check_active(self):
        super()._check_active()
        for company in self:
            if not company.active and company.website_id:
                raise ValidationError(_(
                    'The company %(company_name)r cannot be archived because it has a linked website %(website_name)r.'
                    '\nChange that website\'s company first.',
                    company_name=company.name,
                    website_name=company.website_id.name
                ))

    def google_map_img(self, zoom=8, width=298, height=298):
        partner = self.sudo().partner_id
        return partner and partner.google_map_img(zoom, width, height) or None

    def google_map_link(self, zoom=8):
        partner = self.sudo().partner_id
        return partner and partner.google_map_link(zoom) or None
