from stdnum.cz.dic import compact

from odoo import _, fields
from odoo.tools import date_utils
from odoo.exceptions import RedirectWarning


def get_eu_country_codes(env, options):
    rslt = env.ref('base.europe').country_ids.mapped('code')

    # GB left the EU on January 1st 2021. But before this date, it's still to be considered as a EC country
    if fields.Date.from_string(options['date']['date_from']) < fields.Date.from_string('2021-01-01'):
        rslt.append('GB')
    return rslt


def validate_czech_company_fields(sender_company):
    if not sender_company.l10n_cz_tax_office_id or not sender_company.vat:
        raise RedirectWarning(
            message=_("Please first set a tax office and tax ID on your company."),
            action=sender_company._get_records_action(name=_("Company: %s", sender_company.name), target='new'),
            button_text=_("Go to Company"),
        )


def get_veta_d_vals(report, options):
    report_to_form_mapping = {
        'l10n_cz_reports_2025.control_statement_report': {'document': "KH1", 'control_report_form': "B"},
        'l10n_cz_reports_2025.vies_summary_report': {'document': "SHV", 'vies_report_form': "N"},
        'l10n_cz.l10n_cz_vat_declaration': {'document': "DP3", 'vat_report_form': "B", 'vat_report_submitter_type': "P"},
    }

    date_from = fields.Date.from_string(options['date']['date_from'])
    period_type = options['date']['period_type']
    report_xml_id = report.get_external_id().get(report.id)
    return {
        'quarter': date_utils.get_quarter_number(date_from) if period_type == 'quarter' else None,
        'month': date_from.month if period_type == 'month' else None,
        'year': date_from.year,
        **report_to_form_mapping.get(report_xml_id),
    }


def get_veta_p_vals(sender_company):
    return {
        'workplace_code': sender_company.l10n_cz_tax_office_id.workplace_code,
        'office_code': sender_company.l10n_cz_tax_office_id.code,
        'vat': compact(sender_company.vat),
        'email': sender_company.email,
        'company_type': "F" if sender_company.partner_id.company_type == 'person' else "P",
        'company_name': sender_company.name,
    }
