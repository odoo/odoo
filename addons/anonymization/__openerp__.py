# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Database Anonymization',
    'version': '1.0',
    'category': 'Tools',
    'description': """
This module allows you to anonymize a database.
===============================================

This module allows you to keep your data confidential for a given database.
This process is useful if you want to use the migration process and protect
your own or your customer’s confidential data. The principle is that you run
an anonymization tool which will hide your confidential data(they are replaced
by ‘XXX’ characters). Then you can send the anonymized database to the migration
team. Once you get back your migrated database, you restore it and reverse the
anonymization process to recover your previous data.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base'],
    'init_xml': [],
    'update_xml': [],
    'demo_xml': [
        'anonymization_demo.xml',
    ],
    'data': [
        'ir.model.fields.anonymization.csv',
        'security/ir.model.access.csv',
        'anonymization_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'certificate': '00719010980872226045',
    'images': ['images/anonymization1.jpeg','images/anonymization2.jpeg','images/anonymization3.jpeg'],
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
