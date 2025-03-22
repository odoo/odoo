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
            (f'{company.id}_tax_withhold_profit_312A', '312A 1% Compras al Productor: de Bienes de Origen Bioacuático, Forestal y los Descritos el Art.27.1 de LRTI'),
            (f'{company.id}_tax_withhold_profit_308', '308 10% Utilizacion o Aprovechamiento de la Imagen o Renombre (Personas Naturales,Sociedades,"Influencers")'),
            (f'{company.id}_tax_withhold_profit_3440', '3440 2.75% Otras Retenciones Aplicables el 2,75%')
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
            (f'{company.id}_tax_withhold_profit_3440', '3440', '3940')
        ]
        for xml_id, l10n_ec_code_base, l10n_ec_code_applied in taxes_to_update:
            cr.execute("UPDATE account_tax SET l10n_ec_code_base=%s, l10n_ec_code_applied=%s "
                       "WHERE id=(SELECT res_id FROM ir_model_data WHERE module = 'l10n_ec' AND name=%s)",
                       (l10n_ec_code_base, l10n_ec_code_applied, xml_id))

def inactivate_taxes_replaced(cr, env):
    """
    Inactivate the taxes that were replaced by the new ones
    """

    companies = env['res.company'].search([('chart_template_id', '=', env.ref('l10n_ec.l10n_ec_ifrs').id)])
    for company in companies:
        taxes_to_inactivate = [
            f'{company.id}_tax_withhold_profit_304',  # replaced by tax_withhold_profit_304_10
            f'{company.id}_tax_withhold_profit_304A',  # replaced by tax_withhold_profit_304A_10
            f'{company.id}_tax_withhold_profit_304B',  # replaced by tax_withhold_profit_304B_10
            f'{company.id}_tax_withhold_profit_304E',  # replaced by tax_withhold_profit_304E_10
            f'{company.id}_tax_withhold_profit_309',  # replaced by tax_withhold_profit_309_2_75
            f'{company.id}_tax_withhold_profit_314A',  # replaced by tax_withhold_profit_314A_10
            f'{company.id}_tax_withhold_profit_314B',  # replaced by tax_withhold_profit_314B_10
            f'{company.id}_tax_withhold_profit_314C',  # replaced by tax_withhold_profit_314C_10
            f'{company.id}_tax_withhold_profit_314D',  # replaced by tax_withhold_profit_314D_10
            f'{company.id}_tax_withhold_profit_320',  # replaced by tax_withhold_profit_320_10
            f'{company.id}_tax_withhold_profit_322',  # replaced by tax_withhold_profit_322_1
            f'{company.id}_tax_withhold_profit_319',  # replaced by tax_withhold_profit_319_2
        ]
        for xml_id in taxes_to_inactivate:
            cr.execute("UPDATE account_tax SET active=False "
                       "WHERE id=(SELECT res_id FROM ir_model_data WHERE module = 'l10n_ec' AND name=%s)", (xml_id,))

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    update_taxes_from_templates(cr, 'l10n_ec.l10n_ec_ifrs')
    update_names(cr, env)
    update_ec_codes(cr, env)
    inactivate_taxes_replaced(cr, env)
