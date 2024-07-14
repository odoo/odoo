# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
import csv


def post_init_hook(env):
    mx_country = env["res.country"].search([("code", "=", "MX")])
    # Load cities
    res_city_vals_list = []
    with tools.file_open("l10n_mx_edi_extended/data/res.city.csv") as csv_file:
        for row in csv.DictReader(csv_file, delimiter='|', fieldnames=['l10n_mx_edi_code', 'name', 'state_xml_id']):
            state = env.ref('base.%s' % row['state_xml_id'], raise_if_not_found=False)
            res_city_vals_list.append({
                'l10n_mx_edi_code': row['l10n_mx_edi_code'],
                'name': row['name'],
                'state_id': state.id if state else False,
                'country_id': mx_country.id,
            })

    existing_codes = set(env['res.city'].search([
        ('l10n_mx_edi_code', 'in', [v['l10n_mx_edi_code'] for v in res_city_vals_list])
    ]).mapped('l10n_mx_edi_code'))
    res_city_vals_list = [city for city in res_city_vals_list if city['l10n_mx_edi_code'] not in existing_codes]
    if res_city_vals_list:
        cities = env['res.city'].create(res_city_vals_list)

        env.cr.execute('''
           INSERT INTO ir_model_data (name, res_id, module, model, noupdate)
               SELECT
                    'res_city_mx_' || lower(res_country_state.code) || '_' || res_city.l10n_mx_edi_code,
                    res_city.id,
                    'l10n_mx_edi_extended',
                    'res.city',
                    TRUE
               FROM res_city
               JOIN res_country_state ON res_country_state.id = res_city.state_id
               WHERE res_city.id IN %s
        ''', [tuple(cities.ids)])

    # ==== Load l10n_mx_edi.res.locality ====

    if not env['l10n_mx_edi.res.locality'].search_count([]):
        tariff_fraction_vals_list = []
        with tools.file_open("l10n_mx_edi_extended/data/l10n_mx_edi.res.locality.csv") as csv_file:
            for row in csv.DictReader(csv_file, delimiter='|', fieldnames=['code', 'name', 'state_xml_id']):
                state = env.ref('base.%s' % row['state_xml_id'], raise_if_not_found=False)
                tariff_fraction_vals_list.append({
                    'code': row['code'],
                    'name': row['name'],
                    'state_id': state.id if state else False,
                    'country_id': mx_country.id,
                })

        localities = env['l10n_mx_edi.res.locality'].create(tariff_fraction_vals_list)

        if localities:
            env.cr.execute('''
               INSERT INTO ir_model_data (name, res_id, module, model, noupdate)
                   SELECT 
                        'res_locality_mx_' || lower(res_country_state.code) || '_' || l10n_mx_edi_res_locality.code,
                        l10n_mx_edi_res_locality.id,
                        'l10n_mx_edi_extended',
                        'l10n_mx_edi.res.locality',
                        TRUE
                   FROM l10n_mx_edi_res_locality
                   JOIN res_country_state ON res_country_state.id = l10n_mx_edi_res_locality.state_id
                   WHERE l10n_mx_edi_res_locality.id IN %s
            ''', [tuple(localities.ids)])

    # ==== Load l10n_mx_edi.tariff.fraction ====

    if not env['l10n_mx_edi.tariff.fraction'].search_count([]):
        tariff_fraction_vals_list = []
        with tools.file_open("l10n_mx_edi_extended/data/l10n_mx_edi.tariff.fraction.csv") as csv_file:
            for row in csv.DictReader(csv_file, delimiter='|', fieldnames=['code', 'name', 'uom_code']):
                tariff_fraction_vals_list.append(row)

        tariff_fractions = env['l10n_mx_edi.tariff.fraction'].create(tariff_fraction_vals_list)

        if tariff_fractions:
            env.cr.execute('''
               INSERT INTO ir_model_data (name, res_id, module, model, noupdate)
                   SELECT 
                        'tariff_fraction_' || l10n_mx_edi_tariff_fraction.code,
                        l10n_mx_edi_tariff_fraction.id,
                        'l10n_mx_edi_extended',
                        'l10n_mx_edi.tariff.fraction',
                        TRUE
                   FROM l10n_mx_edi_tariff_fraction
                   WHERE l10n_mx_edi_tariff_fraction.id IN %s
            ''', [tuple(tariff_fractions.ids)])


def uninstall_hook(env):
    env.cr.execute("DELETE FROM ir_model_data WHERE model='l10n_mx_edi.tariff.fraction';")
