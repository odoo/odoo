# coding: utf-8

from openerp import SUPERUSER_ID

def load_translations(cr, registry):
    chart_template = registry['ir.model.data'].xmlid_to_object(cr, SUPERUSER_ID, 'l10n_sa.account_arabic_coa_general')
    chart_template.process_coa_translations()