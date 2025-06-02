from odoo import fields, models, api
import logging

_logger = logging.getLogger(__name__)


class PosSession(models.Model):
    _inherit = 'pos.session'
    ticket_number = fields.Integer(string='Ticket Number', help='A  number that is incremented with each order', default=1)

    def _load_pos_data_fields(self,config_id):
        result = super()._load_pos_data_fields(config_id)
        pos_order = self.env['pos.order']
        ticket_number = pos_order.get_today_ticket_number()
        print("ticket_number", ticket_number)
        result.append('ticket_number')
        return result

