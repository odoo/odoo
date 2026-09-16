# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    square_application_id = fields.Char(
        string="Application ID",
        help="Log into the Square Developer Console then navigate to your application > Credentials",
    )

    def _get_terminal_provider_selection(self):
        return super()._get_terminal_provider_selection() + [('square', 'Square')]

    @api.model
    def _load_pos_data_fields(self, config):
        return [*super()._load_pos_data_fields(config), 'square_application_id']
