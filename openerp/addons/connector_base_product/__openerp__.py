# -*- coding: utf-8 -*-
# © 2014 David BEAL Akretion, Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{'name': 'Connector Base Product',
 'version': '9.0.1.0.0',
 'author': "Openerp Connector Core Editors, Odoo Community Association (OCA)",
 'website': 'http://odoo-connector.com',
 'license': 'AGPL-3',
 'category': 'Connector',
 'description': """
Connector Base Product
======================

Add 'Connector' tab to product view
""",
 'depends': [
     'connector',
     'product',
 ],
 'data': [
     'views/product_view.xml'
 ],
 'installable': True,
 }
