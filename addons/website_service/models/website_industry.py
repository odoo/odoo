# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class WebsiteIndustry(models.Model):

    _name = "website.industry"
    _description = "Website Industry"

    name = fields.Char()
    label = fields.Char()


class WebsiteIndustryThemeLink(models.Model):
    _name = "website.industry.theme.link"
    _description = "link between industry and theme"
    _order = "sequence"

    industry_id = fields.Many2one('website.industry')
    theme_id = fields.Many2one('ir.module.module')
    sequence = fields.Integer()
