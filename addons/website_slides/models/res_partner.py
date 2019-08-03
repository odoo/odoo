# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    slide_channels_count = fields.Integer('Course Count', compute='_compute_slide_channels_count')
    slide_channels_company_count = fields.Integer('Company Course Count', compute='_compute_slide_channels_company_count')

    @api.depends('is_company')
    def _compute_slide_channels_count(self):
        read_group_res = self.env['slide.channel.partner'].sudo().read_group(
            [('partner_id', 'in', self.ids)],
            ['partner_id'], 'partner_id'
        )
        data = dict((res['partner_id'][0], res['partner_id_count']) for res in read_group_res)
        for partner in self:
            partner.slide_channels_count = data.get(partner.id, 0)

    @api.depends('is_company', 'child_ids.slide_channels_count')
    def _compute_slide_channels_company_count(self):
        for partner in self:
            if partner.is_company:
                partner.slide_channels_company_count = self.env['slide.channel'].sudo().search_count(
                    [('partner_ids', 'in', partner.child_ids.ids)]
                )
            else:
                partner.slide_channels_company_count = 0

    def action_view_courses(self):
        action = self.env.ref('website_slides.res_partner_action_courses').read()[0]
        action['view_mode'] = 'tree'
        action['domain'] = ['|', ('partner_ids', 'in', self.ids), ('partner_ids', 'in', self.child_ids.ids)]

        return action
