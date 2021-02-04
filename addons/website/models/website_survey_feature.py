# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class WebsiteSurveyFeature(models.Model):

    _name = "website.survey.feature"
    _description = "Website Survey Feature"
    _order = 'sequence'

    title = fields.Char()
    description = fields.Char()
    code = fields.Char()
    website_type = fields.Char()
    type = fields.Selection([('page', 'Page'), ('app', 'App')])
    module_id = fields.Many2one('ir.module.module', ondelete="cascade")
    page_view_id = fields.Many2one('ir.ui.view', ondelete='cascade')
    sequence = fields.Integer()
