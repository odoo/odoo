from odoo.tools.safe_eval import safe_whitelist

from . import models
from . import tools

safe_whitelist.add_function('odoo.addons.l10n_pl_edi.models.account_move.AccountMove._l10n_pl_edi_get_xml_values.<locals>.get_vat_country')
safe_whitelist.add_function('odoo.addons.l10n_pl_edi.models.account_move.AccountMove._l10n_pl_edi_get_xml_values.<locals>.get_amounts_from_tag')
safe_whitelist.add_function('odoo.addons.l10n_pl_edi.models.account_move.AccountMove._l10n_pl_edi_get_xml_values.<locals>.get_amounts_from_tag_in_PLN_currency')
