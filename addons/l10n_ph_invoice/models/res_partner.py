# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        # SC/PWD ID numbers, recorded on each discounted sale (RR 7-2010
        # Sec. 7, RR 5-2017 Sec. 5.9) from the holder's contact. Deliberately
        # left without a category: 'CN' would clash with the individual's TIN
        # in `vat` (see account's _check_identifier_combination), and any of
        # the legal entity/tax categories would make it eligible as the
        # partner's identifier in EDI exports.
        return {
            **super()._get_all_additional_identifiers_metadata(),
            "PH_SC_ID": {
                "sequence": 200,
                "label": _lt("Senior Citizen ID"),
                "help": _lt("OSCA-issued Senior Citizen ID number (RA 9994)."),
                "countries": ["PH"],
            },
            "PH_PWD_ID": {
                "sequence": 210,
                "label": _lt("Person with Disability ID"),
                "help": _lt("Person with Disability ID number (RA 10754)."),
                "countries": ["PH"],
            },
        }
