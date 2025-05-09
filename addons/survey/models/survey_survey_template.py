# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import api, models, _


class SurveySurvey(models.Model):
    """This model defines additional actions on the 'survey.survey' model that
       can be used to load a survey sample.
    """

    _inherit = 'survey.survey'

    @api.model
    def action_load_sample_custom(self):
        return self.env['survey.survey'].create({
            'survey_type': 'custom',
            'title': '',
        }).action_show_sample()

    def action_show_sample(self):
        action = self.env['ir.actions.act_window']._for_xml_id('survey.action_survey_form')
        action['views'] = [[self.env.ref('survey.survey_survey_view_form').id, 'form']]
        action['res_id'] = self.id
        action['context'] = dict(ast.literal_eval(action.get('context', {})),
            create=False
        )
        return action
