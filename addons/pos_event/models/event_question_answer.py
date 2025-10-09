# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class EventQuestionAnswer(models.Model):
    _name = 'event.question.answer'
    _inherit = ['event.question.answer', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['question_id', 'name', 'sequence']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('question_id', 'in', data['event.question'].ids)]

    @api.model
    def _load_pos_data_dependencies(self):
        return ['event.question']
