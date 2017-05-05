# -*- coding: utf-8 -*-
# © 2011 Raphaël Valyi, Renato Lima, Guewen Baconnier, Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{'name': 'Sale Exception',
 'summary': 'Custom exceptions on sale order',
 'version': '9.0.1.0.0',
 'category': 'Generic Modules/Sale',
 'author': "Akretion, Sodexis, Odoo Community Association (OCA)",
 'website': 'http://www.akretion.com',
 'depends': ['sale'],
 'license': 'AGPL-3',
 'data': [
     'security/ir.model.access.csv',
     'wizard/sale_exception_confirm_view.xml',
     'data/sale_exception_data.xml',
     'views/sale_view.xml',
 ],
 'images': [],
 'installable': True,
 }
