# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons import event, point_of_sale


class EventQuestionAnswer(event.EventQuestionAnswer, point_of_sale.PosLoadMixin):

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['question_id', 'name', 'sequence']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('question_id', 'in', [quest['id'] for quest in data['event.question']['data']])]
