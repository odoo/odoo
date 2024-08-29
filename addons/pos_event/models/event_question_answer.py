# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import event, point_of_sale

from odoo import api, models


class EventQuestionAnswer(models.Model, event.EventQuestionAnswer, point_of_sale.PosLoadMixin):

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['question_id', 'name', 'sequence']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('question_id', 'in', [quest['id'] for quest in data['event.question']['data']])]
