# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import textwrap

from odoo import api, fields, models


class CrmIapLeadIndustry(models.Model):
    """ Industry Tags of Acquisition Rules """
    _name = 'crm.iap.lead.industry'
    _description = 'CRM IAP Lead Industry'
    _order = 'sequence,id'

    name = fields.Char(string='Industry', required=True, translate=True)
    sic_group = fields.Integer(string="SIC Group", required=True, help="Industry's Major Group Code as per SIC")
    division_id = fields.Many2one(
        'crm.iap.lead.industry.division',
        string="SIC Division",
        required=True,
        ondelete='restrict',
        help="SIC Division code to which Major Group belongs.",
    )
    color = fields.Integer(string='Color Index')
    sequence = fields.Integer('Sequence')

    _name_uniq = models.Constraint(
        'unique (name)',
        'Industry name already exists!',
    )

    @api.depends("name", "division_id")
    @api.depends_context("formatted_display_name")
    def _compute_display_name(self):
        needs_markdown = self.env.context.get("formatted_display_name")
        for industry in self:
            if needs_markdown:
                short_industry_name = textwrap.shorten(industry.name, width=40, placeholder="...")
                short_division_name = textwrap.shorten(industry.division_id.name, width=40, placeholder="...")
                industry.display_name = f"{short_industry_name} \v--{short_division_name}--"
            else:
                industry.display_name = industry.name
