# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tools.safe_eval import safe_whitelist

from . import models
from . import wizard

safe_whitelist.add_function('odoo.addons.l10n_hu_edi.models.l10n_hu_edi_connection.format_bool')
