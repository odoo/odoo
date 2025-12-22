from odoo import api, fields, models


class Event(models.Model):
    _name = 'event.event'
    _inherit = ['event.event', 'pos.load.mixin']

    image_1024 = fields.Image("PoS Image", max_width=1024, max_height=1024)

    @api.model
    def _load_pos_data_domain(self, data):
        return [('event_ticket_ids', 'in', [ticket['id'] for ticket in data['event.event.ticket']['data']])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'seats_available', 'event_ticket_ids', 'registration_ids', 'seats_limited', 'write_date',
                'question_ids', 'general_question_ids', 'specific_question_ids', 'badge_format']
