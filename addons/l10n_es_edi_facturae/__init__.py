# Part of Odoo. See LICENSE file for full copyright and licensing details.
import csv

from odoo.tools import file_open
from . import models
from . import wizard


def _l10n_es_edi_facturae_post_init_hook(env):
    """
    We need to replace the existing spanish taxes following the template so the new fields are set properly
    """
    if env['account.tax'].search_count([('country_id', '=', env.ref('base.es').id)], limit=1):
        env['account.tax']._update_l10n_es_edi_facturae_tax_type()
