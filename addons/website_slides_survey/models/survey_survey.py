# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class Survey(models.Model):
    _inherit = 'survey.survey'

    avg_score = fields.Float(string='Avg Score', compute='_compute_avg_score')

    @api.depends('user_input_ids','user_input_ids.quizz_score')
    def _compute_avg_score(self):
        tot = 0
        for record in self:
            nb_user = len(record.user_input_ids)
            for user in record.user_input_ids:
                tot += user.quizz_score
        if nb_user > 0:
            print(tot / nb_user)
            self.avg_score = tot / nb_user

    def _check_answer_creation(self, user, partner, email, test_entry=False, check_attempts=True, invite_token=False):
        """ Overridden to allow website_publisher to test certifications. """
        self.ensure_one()
        if test_entry and user.has_group('website.group_website_publisher'):
            return True

        return super(Survey, self)._check_answer_creation(user, partner, email, test_entry=test_entry, check_attempts=check_attempts, invite_token=invite_token)
