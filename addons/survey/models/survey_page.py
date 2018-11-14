# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SurveyPage(models.Model):
    """ A page for a survey.

        Pages are essentially containers, allowing to group questions by ordered
        screens.

        .. note::
            A page should be deleted if the survey it belongs to is deleted.
    """
    _name = 'survey.page'
    _description = 'Survey Page'
    _rec_name = 'title'
    _order = 'sequence,id'

    # Model Fields #

    title = fields.Char('Page Title', required=True, translate=True)
    survey_id = fields.Many2one('survey.survey', string='Survey', ondelete='cascade', required=True)
    question_ids = fields.One2many('survey.question', 'page_id', string='Questions', copy=True)
    sequence = fields.Integer('Page number', default=10)
    description = fields.Html('Description', translate=True, oldname="note", help="An introductory text to your page")