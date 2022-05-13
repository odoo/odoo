# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    slide_channel_ids = fields.Many2many(
        'slide.channel', 'slide_channel_partner', 'partner_id', 'channel_id',
        string='eLearning Courses', groups="website_slides.group_website_slides_officer")
    slide_channel_completed_ids = fields.One2many(
        'slide.channel', string='Completed Courses',
        compute='_compute_slide_channel_completed_ids',
        search='_search_slide_channel_completed_ids',
        groups="website_slides.group_website_slides_officer")
    slide_channel_count = fields.Integer(
        'Course Count', compute='_compute_slide_channel_count',
        groups="website_slides.group_website_slides_officer")
    slide_channel_company_count = fields.Integer(
        'Company Course Count', compute='_compute_slide_channel_company_count',
        groups="website_slides.group_website_slides_officer")

    def _compute_slide_channel_completed_ids(self):
        for partner in self:
            partner.slide_channel_completed_ids = self.env['slide.channel.partner'].search([
                ('partner_id', '=', partner.id),
                ('completed', '=', True)
            ]).mapped('channel_id')

    def _search_slide_channel_completed_ids(self, operator, value):
        cp_done = self.env['slide.channel.partner'].sudo().search([
            ('channel_id', operator, value),
            ('completed', '=', True)
        ])
        return [('id', 'in', cp_done.partner_id.ids)]

    @api.depends('is_company')
    def _compute_slide_channel_count(self):
        read_group_res = self.env['slide.channel.partner'].sudo()._read_group(
            [('partner_id', 'in', self.ids)],
            ['partner_id'], 'partner_id'
        )
        data = dict((res['partner_id'][0], res['partner_id_count']) for res in read_group_res)
        for partner in self:
            partner.slide_channel_count = data.get(partner.id, 0)

    @api.depends('is_company', 'child_ids.slide_channel_count')
    def _compute_slide_channel_company_count(self):
        for partner in self:
            if partner.is_company:
                partner.slide_channel_company_count = self.env['slide.channel'].sudo().search_count(
                    [('partner_ids', 'in', partner.child_ids.ids)]
                )
            else:
                partner.slide_channel_company_count = 0

    def action_view_courses(self):
        """ View partners courses. In singleton mode, return courses followed
        by all its contacts (if company) or by themselves (if not a company).
        Otherwise simply set a domain on required partners. """
        action = self.env["ir.actions.actions"]._for_xml_id("website_slides.slide_channel_partner_action")
        action['name'] = _('Followed Courses')
        if len(self) == 1 and self.is_company:
            action['domain'] = [('partner_id', 'in', self.child_ids.ids)]
        elif len(self) == 1:
            action['context'] = {'search_default_partner_id': self.id}
        else:
            action['domain'] = [('partner_id', 'in', self.ids)]
        return action
