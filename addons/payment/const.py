# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _


REPORT_REASONS_MAPPING = {
    'exceed_max_amount': _("maximum amount exceeded"),
    'express_checkout_not_supported': _("express checkout not supported"),
    'incompatible_country': _("incompatible country"),
    'incompatible_currency': _("incompatible currency"),
    'incompatible_website': _("incompatible website"),
    'manual_capture_not_supported': _("manual capture not supported"),
    'provider_not_available': _("no supported provider available"),
    'tokenization_not_supported': _("tokenization not supported"),
    'validation_not_supported': _("tokenization without payment no supported"),
}
