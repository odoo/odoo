# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from odoo import api, SUPERUSER_ID
import logging

_logger = logging.getLogger(__name__)


def _l10n_it_edi_doi_post_init(cr, registry):
    """ Update existing companies that have the Italian Chart of Accounts set """
    env = api.Environment(cr, SUPERUSER_ID, {})
    chart_template = env.ref('l10n_it.l10n_it_chart_template_generic', raise_if_not_found=False)
    if chart_template:
        for company in env['res.company'].search([('chart_template_id', '=', chart_template.id)]):
            _logger.info("Company %s already has the Italian localization installed, updating...", company.name)

            # Create the declaration of intent fiscal position
            doi_fp_template = env.ref('l10n_it_edi_doi.declaration_of_intent_fiscal_position')
            doi_fp_vals = ((doi_fp_template, chart_template._get_fp_vals(company, doi_fp_template)),)
            doi_fp = chart_template._create_records_with_xmlid('account.fiscal.position', doi_fp_vals, company)

            # Create the declaration of intent tax
            doi_tax_template = env.ref('l10n_it_edi_doi.00di')
            tax_template_ref = doi_tax_template._generate_tax(company)['tax_template_to_tax']
            doi_tax = tax_template_ref[doi_tax_template]
            doi_tax.write({
                'l10n_it_has_exoneration': True,
                'l10n_it_kind_exoneration': 'N3.5',
                'l10n_it_law_reference': 'art. 8, c. 1, lett. c) D.P.R. 633/1972',
            })

            # Create the fiscal position tax mappings
            # Add all the taxes needed for the fiscal position to `tax_template_ref`
            for tax_template_id, external_xml_id in doi_fp_template.tax_ids.tax_src_id.get_external_id().items():
                tax_template = env['account.tax.template'].browse(tax_template_id)
                module, xml_id = external_xml_id.split('.')
                tax = env.ref('%s.%s_%s' % (module, company.id, xml_id), raise_if_not_found=False)
                if tax:
                    tax_template_ref[tax_template] = tax
            # Gather all the info for the tax mappings
            doi_fp_tax_template_vals = []
            for tax in doi_fp_template.tax_ids:
                tax_src_id = tax_template_ref.get(tax.tax_src_id)
                tax_dest_id = tax_template_ref.get(tax.tax_dest_id)
                if tax_src_id is None or tax_dest_id is None:
                    continue
                doi_fp_tax_template_vals.append((tax, {
                    'tax_src_id': tax_src_id.id,
                    'tax_dest_id': tax_dest_id.id or False,
                    'position_id': doi_fp.id,
                }))
            chart_template._create_records_with_xmlid('account.fiscal.position.tax', doi_fp_tax_template_vals, company)

            # Set the info on the company
            company.l10n_it_edi_doi_tax_id = doi_tax
            company.l10n_it_edi_doi_fiscal_position_id = doi_fp
