"""KSW Commissions general settings — meal allowance unit prices.

Extends ``res.config.settings`` with three configurable unit prices
used by the Technician Location Allowance calculator:

  * Breakfast (default 10 SAR)
  * Lunch     (default 20 SAR)
  * Dinner    (default 15 SAR)

Storage is delegated to ``ir.config_parameter`` so the values are
global, persistent and easy to change at any time without code
changes.  Future general configuration toggles for KSW_commissions
can live on this same settings record.
"""
from odoo import api, fields, models


PARAM_BREAKFAST = 'KSW_commissions.meal_breakfast_price'
PARAM_LUNCH = 'KSW_commissions.meal_lunch_price'
PARAM_DINNER = 'KSW_commissions.meal_dinner_price'

DEFAULT_BREAKFAST = 10.0
DEFAULT_LUNCH = 20.0
DEFAULT_DINNER = 15.0


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ksw_meal_breakfast_price = fields.Float(
        string='Breakfast Price',
        config_parameter=PARAM_BREAKFAST,
        default=DEFAULT_BREAKFAST,
        help='Unit price (SAR) per breakfast occurrence on a '
             'technician location-allowance line.',
    )
    ksw_meal_lunch_price = fields.Float(
        string='Lunch Price',
        config_parameter=PARAM_LUNCH,
        default=DEFAULT_LUNCH,
        help='Unit price (SAR) per lunch occurrence on a '
             'technician location-allowance line.',
    )
    ksw_meal_dinner_price = fields.Float(
        string='Dinner Price',
        config_parameter=PARAM_DINNER,
        default=DEFAULT_DINNER,
        help='Unit price (SAR) per dinner occurrence on a '
             'technician location-allowance line.',
    )

    # ------------------------------------------------------------------
    # Helpers (used by ksw.location.allowance.line computes)
    # ------------------------------------------------------------------
    @api.model
    def _get_meal_prices(self):
        """Return ``(breakfast, lunch, dinner)`` floats from the
        ``ir.config_parameter`` store, falling back to the defaults
        when a key is missing or non-numeric.
        """
        ICP = self.env['ir.config_parameter'].sudo()

        def _read(key, default):
            raw = ICP.get_param(key)
            if raw in (False, None, ''):
                return default
            try:
                return float(raw)
            except (TypeError, ValueError):
                return default

        return (
            _read(PARAM_BREAKFAST, DEFAULT_BREAKFAST),
            _read(PARAM_LUNCH, DEFAULT_LUNCH),
            _read(PARAM_DINNER, DEFAULT_DINNER),
        )

