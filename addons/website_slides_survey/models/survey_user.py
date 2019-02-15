# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    slide_id = fields.Many2one('slide.slide', 'Related course slide',
        help="The related course slide when there is no membership information")
    slide_partner_id = fields.Many2one('slide.slide.partner', 'Subscriber information',
        help="Slide membership information for the logged in user")
