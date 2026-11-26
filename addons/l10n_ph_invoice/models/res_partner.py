# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

# They have no 'category' and are not 'synced': they are personal IDs that must neither be
# elected as the legal entity identifier of the contact, nor be copied to its other contacts.
PH_PRIVILEGE_IDENTIFIERS_METADATA = {
    "PH_PWD_ID": {
        "sequence": 200,
        "label": _lt("PWD ID"),
        "help": _lt("Identification number of a Person with Disability (PWD)."),
        "countries": ["PH"],
        "synced": False,
    },
    "PH_SC_ID": {
        "sequence": 201,
        "label": _lt("Senior Citizen ID"),
        "help": _lt("Identification number of a Senior Citizen (SC)."),
        "countries": ["PH"],
        "synced": False,
    },
    "PH_NCAA_ID": {
        "sequence": 202,
        "label": _lt("NCAA ID"),
        "countries": ["PH"],
        "synced": False,
    },
    "PH_SOLO_PARENT_ID": {
        "sequence": 203,
        "label": _lt("Solo Parent ID"),
        "help": _lt("Identification number of a Solo Parent."),
        "countries": ["PH"],
        "synced": False,
    },
    "PH_MEDAL_OF_VALOR_ID": {
        "sequence": 204,
        "label": _lt("Medal of Valor ID"),
        "help": _lt("Identification number of a Medal of Valor awardee."),
        "countries": ["PH"],
        "synced": False,
    },
}


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _get_all_additional_identifiers_metadata(self):
        return {**super()._get_all_additional_identifiers_metadata(), **PH_PRIVILEGE_IDENTIFIERS_METADATA}
