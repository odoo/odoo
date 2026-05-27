# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import SQL


class PosConfig(models.Model):
    _inherit = "pos.config"

    l10n_ph_basic_can_close_register = fields.Boolean(
        string="Allow Close Register for Basic Rights User",
        help="Allow employees with basic rights to close the current PoS register.",
    )

    company_currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Company Currency",
        readonly=True,
    )
    l10n_ph_accumulated_total_sales = fields.Monetary(
        string="Accumulated Grand Total Sales",
        help="Total sales for this point of sale since inception.",
        currency_field="company_currency_id",
    )

    l10n_ph_void_counter = fields.Integer(
        string="Void Counter",
        copy=False,
        help="Number of line void transactions for this POS configuration.",
    )

    l10n_ph_machine_identification_number = fields.Char(
        string="Machine Identification Number",
        help="Internal Reference for this Point of Sale.",
    )

    l10n_ph_machine_serial_number = fields.Char(
        string="Machine Serial Number",
        help="Serial Number associated with this machine.",
    )

    @api.depends(
        "l10n_ph_basic_can_close_register",
        "l10n_ph_accumulated_total_sales",
        "l10n_ph_void_counter",
        "l10n_ph_machine_identification_number",
        "l10n_ph_machine_serial_number",
    )
    def _compute_local_data_integrity(self):
        return super()._compute_local_data_integrity()

    def _l10n_ph_add_accumulated_total_sales(self, totals_by_config):
        """Atomically increment accumulated total sales for given config IDs.

        :param totals_by_config: mapping of config_id -> amount to add
        """
        for config_id, increment in totals_by_config.items():
            if not increment:
                continue
            self.env.cr.execute(
                SQL(
                    """
                UPDATE pos_config
                   SET l10n_ph_accumulated_total_sales = COALESCE(l10n_ph_accumulated_total_sales, 0) + %s
                 WHERE id = %s
                """,
                    increment,
                    config_id,
                ),
            )
        if totals_by_config:
            self.env["pos.config"].browse(list(totals_by_config)).invalidate_recordset(
                ["l10n_ph_accumulated_total_sales"],
            )
