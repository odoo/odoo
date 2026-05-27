# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    company_currency_id = fields.Many2one(
        related="pos_config_id.company_currency_id",
        readonly=True,
    )
    l10n_ph_accumulated_total_sales = fields.Monetary(
        related="pos_config_id.l10n_ph_accumulated_total_sales",
        currency_field="company_currency_id",
        readonly=True,
    )

    l10n_ph_void_counter = fields.Integer(
        related="pos_config_id.l10n_ph_void_counter",
        readonly=True,
    )

    pos_l10n_ph_basic_can_close_register = fields.Boolean(
        related="pos_config_id.l10n_ph_basic_can_close_register",
        readonly=False,
    )

    pos_l10n_ph_machine_identification_number = fields.Char(
        related="pos_config_id.l10n_ph_machine_identification_number",
        readonly=False,
    )

    pos_l10n_ph_machine_serial_number = fields.Char(
        related="pos_config_id.l10n_ph_machine_serial_number",
        readonly=False,
    )
