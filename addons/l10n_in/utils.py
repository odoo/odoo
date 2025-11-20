import re
from odoo.tools.float_utils import json_float_round


def l10n_in_extract_digits(string):
    if not string:
        return ""
    matches = re.findall(r"\d+", string)
    return "".join(matches)


def l10n_in_get_tax_details_by_line_code(tax_details):
    l10n_in_tax_details = {}
    for tax_detail in tax_details.values():
        if tax_detail["tax"].l10n_in_reverse_charge:
            l10n_in_tax_details.setdefault("is_reverse_charge", True)
        line_code = tax_detail["line_code"]
        l10n_in_tax_details.setdefault("%s_rate" % (line_code), tax_detail["tax"].amount)
        l10n_in_tax_details.setdefault("%s_amount" % (line_code), 0.00)
        l10n_in_tax_details.setdefault("%s_amount_currency" % (line_code), 0.00)
        l10n_in_tax_details["%s_amount" % (line_code)] += tax_detail["tax_amount"]
        l10n_in_tax_details["%s_amount_currency" % (line_code)] += tax_detail["tax_amount_currency"]
    return l10n_in_tax_details


def l10n_in_is_service_hsn(hsn_code):
    return l10n_in_extract_digits(hsn_code).startswith('99')


def l10n_in_round_value(amount, precision_digits=2):
    return json_float_round(amount, precision_digits)
