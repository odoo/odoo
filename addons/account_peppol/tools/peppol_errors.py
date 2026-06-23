from types import MappingProxyType

from markupsafe import Markup

from odoo import _, _lt


ERROR_MESSAGES = MappingProxyType({
    'PEPPOL-EN16931-P0105': lambda move: Markup(
        _lt(
            "For tax(es) %(taxes)s: Tax Category 'O' must be used when the exemption "
            "reason code is 'VATEX-EU-O'. You can change this in the Advanced Options "
            "of the tax configuration."
        )
    ) % {'taxes': _format_wrong_exempted_taxes(move, 'O', 'VATEX-EU-O')},
    'BR-47': _lt(
        "Missing VAT category code. Action Required: Install the module account_edi_ubl_cii_tax_extension."
    ),
    'BR-O-02': _lt(
        "If you are not subject to VAT, you should not have a VAT number on your company/contacts and your clients should have one either."
    ),
    'BR-O-05': _lt(
        "Invoice lines using Tax Category 'O' (or 'E') cannot use a percentage-based tax. Please update the tax type in Advanced Options."
    ),
    'BR-CO-04': _lt(
        "Missing Invoiced Item VAT category code. Action Required: Install the module account_edi_ubl_cii_tax_extension."
    ),
    'PEPPOL-EN16931-R010': _lt(
        "The Peppol endpoint is missing in the XML file. Action Required: Update the account and account_edi_ubl_cii modules to resolve this."
    ),
    'PEPPOL-EN16931-P0107': _lt(
        "The Tax Category must be 'AE' when using Exemption Reason code 'VATEX-EU-AE'. "
        "You can change this in the Advanced Options of the tax configuration."
    ),
    'BR-S-05': _lt(
        "A 0% tax cannot use Tax Category 'S' (Standard). Please update the Tax Category in the Advanced Options of the tax configuration."
    ),
    'BR-CL-22': _lt(
        "The exemption reason code is invalid. Action Required: Install the module account_edi_ubl_cii_tax_extension."
    ),
    'BR-11': _lt(
        "Missing Buyer Country. Please add the Country Code to the client's contact information."
    ),
    'BR-AE-05': _lt(
        "Invoice lines with Tax Category 'Reverse charge' must have a tax rate of 0. "
        "You can change this in the Advanced Options of the tax configuration."
    ),
    'BR-AE-10': _lt(
        "Missing Reverse Charge details. "
        "Please set the Exemption Reason to 'Reverse charge' in the Advanced Options of the tax configuration."
    ),
    'BR-E-05': _lt(
        "Invoice lines with Tax Category 'Exempt from VAT' must have a tax rate of 0. "
        "You can change this in the Advanced Options of the tax configuration."
    ),
})


def _format_wrong_exempted_taxes(move, category, reason):
    reason_codes = {reason, reason.replace('-', '_')}
    taxes = move.invoice_line_ids.tax_ids.filtered(
        lambda tax:
            'ubl_cii_tax_category_code' in tax._fields
            and tax.ubl_cii_tax_category_code != category
            and tax.ubl_cii_tax_exemption_reason_code in reason_codes
    )
    taxes = [tax._get_html_link() for tax in taxes]
    return Markup(', ').join(taxes)


def _humanize_error_line(raw_line, move):
    for error_code, error_message in ERROR_MESSAGES.items():
        if f'[{error_code}]' in raw_line:
            return error_message(move) if callable(error_message) else error_message
    return raw_line


def render_peppol_errors(error, move):
    raw_message = error.get('data', {}).get('message') or error['message']

    header_lines, error_lines = [], []
    for line in raw_message.split('\n'):
        if line.startswith('['):
            error_lines.append(line)
        else:
            header_lines.append(line)

    body = Markup('<strong>%s</strong><br/>') % _('Peppol error:')
    body += Markup('<br/>').join(header_lines)
    if error_lines:
        items = Markup('').join(
            Markup('<li>%s</li>') % _humanize_error_line(line, move)
            for line in error_lines
        )
        body += Markup('<ul>%s</ul>') % items
    return body
