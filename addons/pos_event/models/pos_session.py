# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config):
        models = super()._load_pos_data_models(config)
        models += ['event.event.ticket', 'event.event', 'event.slot', 'event.registration', 'event.question', 'event.question.answer', 'event.registration.answer']
        return models

    @api.model
    def _load_pos_data_relations(self, model, fields):
        relations = super()._load_pos_data_relations(model, fields)
        if model == 'event.registration':
            # Force compute to False otherwise the frontend will not send the data
            relations['email']['compute'] = False
            relations['phone']['compute'] = False
            relations['name']['compute'] = False
            relations['company_name']['compute'] = False
            relations['event_slot_id']['compute'] = False
        return relations
