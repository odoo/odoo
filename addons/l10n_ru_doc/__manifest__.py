# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-2018 CodUP (<http://codup.com>).
#
##############################################################################

{
    'name': 'Russia - Documents',
    'version': '3.5',
    'summary': 'Первичные документы',
    'description': """
The module for print documents in accordance laws of Russia.
============================================================
Возможности:
    * Товарная накладная (ТОРГ-12)
    * Счет на оплату
    * Счет-фактура
    * Акт выполненных работ
    * Вывод подписей и печати
    """,
    'author': 'CodUP',
    'website': 'http://codup.com',
    'license': 'AGPL-3',
    'category': 'Localization',
    'sequence': 0,
    'depends': ['sale_management'],
    'demo': ['l10n_ru_doc_demo.xml'],
    'data': [
        'account_invoice_view.xml',
        'res_partner_view.xml',
        'res_company_view.xml',
        'res_users_view.xml',
        'res_bank_view.xml',
        'l10n_ru_doc_data.xml',
        'report/l10n_ru_doc_report.xml',
        'report/report_order.xml',
        'report/report_invoice.xml',
        'report/report_bill.xml',
        'report/report_act.xml',
        'edi/bill_action_data.xml',
    ],
    'css': ['static/src/css/l10n_ru_doc.css'],
    'installable': True,
}
