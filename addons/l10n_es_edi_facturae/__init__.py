# Part of Odoo. See LICENSE file for full copyright and licensing details.
import csv

from odoo.tools import file_open
from . import models
from . import wizard

def _edit_tax_types(env, template_data):
    """
    Applies all existing tax l10n_es_edi_facturae_tax_type field to their proper value if any link between tax and their template is found
    """
    concerned_company_ids = [
        company.id
        for company in env.companies
        if company.chart_template and company.chart_template.startswith('es_')
    ]
    if not concerned_company_ids:
        return
    current_taxes = env['account.tax'].search(env['account.tax']._check_company_domain(concerned_company_ids))
    if not current_taxes:
        return
    xmlid2tax = {
        xml_id.split('.')[1].split('_', maxsplit=1)[1]: env['account.tax'].browse(record)
        for record, xml_id in current_taxes.get_external_id().items() if xml_id
    }
    for xmlid, values in template_data.items():
        # Only update the tax_type fields
        oldtax = xmlid2tax.get(xmlid)
        if oldtax and oldtax.l10n_es_edi_facturae_tax_type != values.get('l10n_es_edi_facturae_tax_type'):
            oldtax.l10n_es_edi_facturae_tax_type = values.get('l10n_es_edi_facturae_tax_type')

def _l10n_es_edi_facturae_post_init_hook(env):
    """
    We need to replace the existing spanish taxes following the template so the new fields are set properly
    """
    if env['account.tax'].search_count([('country_id', '=', env.ref('base.es').id)], limit=1):
        with file_open('l10n_es_edi_facturae/data/template/account.tax-es_common.csv') as template_file:
            template_data = {record['id']: record['l10n_es_edi_facturae_tax_type'] for record in csv.DictReader(template_file)}
        _edit_tax_types(env, template_data)
