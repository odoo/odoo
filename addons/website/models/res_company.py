# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


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

    def google_map_img(self, zoom=8, width=298, height=298):
        partner = self.sudo().partner_id
        return partner and partner.google_map_img(zoom, width, height) or None

    def google_map_link(self, zoom=8):
        partner = self.sudo().partner_id
        return partner and partner.google_map_link(zoom) or None

    def _get_public_user(self):
        self.ensure_one()
        # We need sudo to be able to see public users from others companies too
        public_users = self.env.ref('base.group_public').sudo().with_context(active_test=False).users
        public_users_for_website = public_users.filtered(lambda user: user.company_id == self)

        if public_users_for_website:
            return public_users_for_website[0]
        else:
            return self.env.ref('base.public_user').sudo().copy({
                'name': 'Public user for %s' % self.name,
                'login': 'public-user@company-%s.com' % self.id,
                'company_id': self.id,
                'company_ids': [(6, 0, [self.id])],
            })
