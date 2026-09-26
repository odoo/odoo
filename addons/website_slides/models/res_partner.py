# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    slide_channel_ids = fields.Many2many(
        'slide.channel', string='eLearning Courses',
        compute='_compute_slide_channel_values',
        search='_search_slide_channel_ids',
        groups="website_slides.group_website_slides_officer")
    slide_channel_completed_ids = fields.One2many(
        'slide.channel', string='Completed Courses',
        compute='_compute_slide_channel_values',
        search='_search_slide_channel_completed_ids',
        groups="website_slides.group_website_slides_officer")
    slide_channel_count = fields.Integer(
        'Course Count', compute='_compute_slide_channel_values',
        groups="website_slides.group_website_slides_officer")
    # slide_channel_company_count has been generalized to descendant channel count
    # To be renamed in master
    slide_channel_company_count = fields.Integer(
        'Company Course Count', compute='_compute_slide_channel_company_count',
        groups="website_slides.group_website_slides_officer")

    def _compute_slide_channel_values(self):
        data = {
            (partner.id, member_status): channel_ids
            for partner, member_status, channel_ids in self.env['slide.channel.partner'].sudo()._read_group(
                domain=[('partner_id', 'in', self.ids), ('member_status', '!=', 'invited')],
                groupby=['partner_id', 'member_status'],
                aggregates=['channel_id:array_agg']
            )
        }

        for partner in self:
            slide_channel_ids = data.get((partner.id, 'joined'), []) + data.get((partner.id, 'ongoing'), []) + data.get((partner.id, 'completed'), [])
            partner.slide_channel_ids = slide_channel_ids
            partner.slide_channel_completed_ids = self.env['slide.channel'].browse(data.get((partner.id, 'completed'), []))
            partner.slide_channel_count = len(slide_channel_ids)

    def _search_slide_channel_completed_ids(self, operator, value):
        cp_done = self.env['slide.channel.partner'].sudo().search([
            ('channel_id', operator, value),
            ('member_status', '=', 'completed')
        ])
        return [('id', 'in', cp_done.partner_id.ids)]

    def _search_slide_channel_ids(self, operator, value):
        cp_enrolled = self.env['slide.channel.partner'].search([
            ('channel_id', operator, value),
            ('member_status', '!=', 'invited')
        ])
        return [('id', 'in', cp_enrolled.partner_id.ids)]

    @api.depends('is_company', 'child_ids.slide_channel_count')
    def _compute_slide_channel_company_count(self):
        for partner in self:
            partner.slide_channel_company_count = self.env['slide.channel'].sudo().search_count(
                [('partner_ids', 'child_of', partner.ids)]
            )

    def action_view_courses(self):
        """ View partners courses. Return courses followed
        by themselves and all its descendants. The courses to which
        the partner(s) is not enrolled (e.g. invited) are not shown."""
        action = self.env["ir.actions.actions"]._for_xml_id("website_slides.slide_channel_partner_action")
        action['display_name'] = _('Courses')
        action['domain'] = [
            ('member_status', '!=', 'invited'),
            ('partner_id', 'child_of', self.ids),
        ]
        return action
