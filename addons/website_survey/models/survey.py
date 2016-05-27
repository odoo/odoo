# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models

class survey_survey(models.Model):
	_inherit="survey.survey"
	_description = 'Survey'

	@api.multi
	def action_test_survey(self):
	    ''' Open the website page with the survey form into test mode'''
	    self.ensure_one()
	    return {
	        'type': 'ir.actions.act_url',
	        'name': "Results of the Survey",
	        'target': 'self',
	        'url': self.with_context(relative_url=True).public_url + "/phantom"
	    }
