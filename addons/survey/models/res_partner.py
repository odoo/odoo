# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    certifications_count = fields.Integer('Certifications Count', compute='_compute_certifications_count')

    @api.depends('parent_id')
    def _compute_certifications_count(self):
        read_group_res = self.env['survey.user_input'].sudo()._read_group(
            [('partner_id', 'in', self.ids), ('scoring_success', '=', True)],
            ['partner_id'], ['__count']
        )
        data = {partner.id: count for partner, count in read_group_res}
        for partner in self:
            partner.certifications_count = data.get(partner.id, 0)

    def action_view_certifications(self):
        action = self.env["ir.actions.actions"]._for_xml_id("survey.res_partner_action_certifications")
        action['view_mode'] = 'list'
        action['domain'] = ['|', ('partner_id', 'in', self.ids), ('partner_id', 'in', self.child_ids.ids)]

        return action
