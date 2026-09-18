# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Company Currency",
        readonly=True,
    )
    l10n_ph_accumulated_total_sales = fields.Monetary(
        string="Accumulated Grand Total Sales",
        help="Total sales for this point of sale since inception.",
        currency_field="company_currency_id",
        copy=False,
    )

    l10n_ph_machine_identification_number = fields.Char(
        string="Machine Identification Number",
        help="Internal Reference for this Point of Sale.",
        copy=False,
    )

    l10n_ph_machine_serial_number = fields.Char(
        string="Machine Serial Number",
        help="Serial Number associated with this machine.",
        copy=False,
    )

    @api.depends(
        "l10n_ph_accumulated_total_sales",
        "l10n_ph_machine_identification_number",
        "l10n_ph_machine_serial_number",
    )
    def _compute_local_data_integrity(self):
        return super()._compute_local_data_integrity()

    def _l10n_ph_add_accumulated_total_sales(self, totals_by_config):
        """Increment accumulated total sales for given config IDs.

        :param totals_by_config: mapping of config_id -> amount to add
        """
        for config_id, increment in totals_by_config.items():
            if not increment:
                continue
            config = self.browse(config_id)
            config.l10n_ph_accumulated_total_sales = (
                config.l10n_ph_accumulated_total_sales or 0
            ) + increment
