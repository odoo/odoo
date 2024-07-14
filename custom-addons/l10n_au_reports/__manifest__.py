# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Australian Reports - Accounting',
    'countries': ['au'],
    'version': '1.1',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Australian Accounting Module
============================

Taxable Payments Annual Reports (TPAR) for Australia

The Taxable payments annual report (TPAR) allows:

    • Payments made to contractors (or subcontractors) for services, or
    • Grants paid by government entities to ABN holders

to be reported where required under the Taxable Payments Reporting System (TPRS) and the Taxable Government Grants and Payments reporting measure.

The TPAR is due by 28th August each year.

Penalties may apply if you don’t lodge your TPAR on time.

For further information on who is required to lodge a Taxable payments annual report refer to
https://softwaredevelopers.ato.gov.au/tprs

The annual report must be provided to the Commissioner no later than 28 August after the end of the financial year. Reports can be sent more frequently for those that wish to do so.

The report uses tax tags ``Service`` and ``Tax Withheld`` in order to find adequate journal items. These are set using the fiscal positions, and the right type of product (Services).
    """,
    'depends': [
        'l10n_au',
        'account_reports',
        'account_reports_cash_basis',
    ],
    'data': [
        'data/tpar_report.xml',
        'views/menuitems.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_au', 'account_reports'],
    'license': 'OEEL-1',
}
