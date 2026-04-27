# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    starshipit_parcel_reference = fields.Char("Starshipit Parcel Reference", copy=False)
    starshipit_return_parcel_reference = fields.Char("Starshipit Return Parcel Reference", copy=False)

    @api.model
    def _cron_starshipit_fetch_and_update_prices(self, auto_commit=True):
        """
        Cron job to trigger price updates for pickings with pending Starshipit prices.
        """
        pickings_by_carrier = self.env['stock.picking']._read_group(
            domain=[
                ('carrier_price', '=', 0.0),
                ('starshipit_parcel_reference', '!=', False),
                ('delivery_type', '=', 'starshipit'),
                ('state', 'not in', ('cancel', 'draft'))
            ],
            groupby=['carrier_id'],
            aggregates=['id:recordset']
        )
        total_pickings = sum(len(pickings_for_carrier) for _, pickings_for_carrier in pickings_by_carrier)
        _logger.info("Starshipit Cron: Found %s picking(s) with pending price(s).", total_pickings)

        for carrier, pickings_for_carrier in pickings_by_carrier:
            try:
                carrier.get_starshipit_price_update(pickings_for_carrier)
                if auto_commit:
                    self.env.cr.commit()
            except Exception:
                _logger.exception("Starshipit Cron: Error processing pickings for carrier %s", carrier.name)
                if auto_commit:
                    self.env.cr.rollback()

        _logger.info("Starshipit Cron: Finished processing pending prices.")
        return True
