# Author: Eimantas Nėjus. Copyright: JSC Focusate.
# Co-Authors: Silvija Butko, Andrius Laukavičius. Copyright: JSC Focusate
# See LICENSE file for full copyright and licensing details.
{
    'name': 'Lithuania - Accounting Reports',
    'version': '1.0.0',
    'description': """
Accounting reports for Lithuania

Contains Balance Sheet, Profit/Loss reports
    """,
    'license': 'OEEL-1',
    'author': "Focusate",
    'website': "http://www.focusate.eu",
    'category': 'Accounting/Localizations/Reporting',
    'depends': [
        'account_reports',
        'l10n_lt'
    ],
    'data': [
        'data/account_financial_html_report_data.xml',
        'data/account_report_ec_sales_list_report.xml'
    ],
    'auto_install': ['l10n_lt', 'account_reports'],
    'installable': True,
}
