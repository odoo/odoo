# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class QuizPartnerMixin(models.Model):
    _name = 'quiz.partner.mixin'
    _description = ''

    quiz_completed = fields.Boolean('Completed')
    quiz_attempts_count = fields.Integer('Quiz attempts count', default=0)
    karma_gained = fields.Integer("Karma gained on this quiz", default=0)
    points_gained = fields.Integer("Points gained on this quiz", default=0)


class QuizConfigMixin(models.Model):
    _name = 'quiz.config.mixin'
    _description = ''

    unlimited_attempt = fields.Boolean('Unlimited number of attempts', default=False)
    quiz_max_attempts = fields.Integer('Maximum number of attempts for the quiz', default=1)
    quiz_first_attempt_reward = fields.Integer("Reward: first attempt", default=10)
    quiz_second_attempt_reward = fields.Integer("Reward: second attempt", default=7)
    quiz_third_attempt_reward = fields.Integer("Reward: third attempt", default=5,)
    quiz_fourth_attempt_reward = fields.Integer("Reward: every attempt after the third try", default=2)
