# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.models.chart_template import update_taxes_from_templates
from odoo import api, SUPERUSER_ID


def update_names(cr, env):
    """
    Update the names in the taxes
    """
    companies = env['res.company'].search([('chart_template_id', '=', env.ref('l10n_ec.l10n_ec_ifrs').id)])
    for company in companies:
        taxes_to_update = [
            (f'{company.id}_tax_vat_05_411_goods', 'IVA 5% (435, Bienes)'),
            (f'{company.id}_tax_vat_05_510_sup_01', 'IVA 5% (550, 01 Crédito IVA)')
        ]
        for xml_id, name in taxes_to_update:
            # There is no translation for name taxes in the l10n_ec data, which means we need to update the name for each language.
            active_langs = env['res.lang'].search([('active', '=', True)])
            for lang in active_langs:
                tax = env.ref(f'l10n_ec.{xml_id}', raise_if_not_found=False)
                if tax:
                    tax.with_context(lang=lang.code).name = name


def update_ec_codes(cr, env):
    """
    Update special fields for Ecuador, the code base and code applied in the taxes
    """
    companies = env['res.company'].search([('chart_template_id', '=', env.ref('l10n_ec.l10n_ec_ifrs').id)])
    for company in companies:
        taxes_to_update = [
            (f'{company.id}_tax_vat_05_411_goods', '435', '445'),
            (f'{company.id}_tax_vat_05_510_sup_01', '550', '560'),
        ]
        for xml_id, l10n_ec_code_base, l10n_ec_code_applied in taxes_to_update:
            cr.execute("UPDATE account_tax SET l10n_ec_code_base=%s, l10n_ec_code_applied=%s "
                       "WHERE id=(SELECT res_id FROM ir_model_data WHERE module = 'l10n_ec' AND name=%s)",
                       (l10n_ec_code_base, l10n_ec_code_applied, xml_id))


def migrate(cr, version):
    # For May Withholding Tax Code Updates
    env = api.Environment(cr, SUPERUSER_ID, {})
    update_taxes_from_templates(cr, 'l10n_ec.l10n_ec_ifrs')
    update_ec_codes(cr, env)
    update_names(cr, env)
