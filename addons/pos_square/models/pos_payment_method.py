# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging

from odoo import fields, models
from odoo.exceptions import AccessDenied

_logger = logging.getLogger(__name__)
TIMEOUT = 10


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    square_application_id = fields.Char(string="Application ID", help="")
    square_latest_response = fields.Char(copy=False, groups='base.group_erp_manager')  # used to buffer the latest asynchronous notification from Square.

    def _get_payment_terminal_selection(self):
        return super()._get_payment_terminal_selection() + [('square', 'Square')]

    def _is_write_forbidden(self, fields):
        return super()._is_write_forbidden(fields - {'square_latest_response'})

    def _load_pos_data_fields(self, config):
        return [*super()._load_pos_data_fields(config), 'square_application_id']

    def get_latest_square_status(self):
        self.ensure_one()
        if not self.env.su and not self.env.user.has_group('point_of_sale.group_pos_user'):
            raise AccessDenied()

        latest_response = self.sudo().square_latest_response
        return json.loads(latest_response) if latest_response else False
