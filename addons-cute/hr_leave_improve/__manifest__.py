# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Time Off Improve ',
    'version': '1.5',
    'category': 'Human Resources/Time Off Improve',
    'sequence': 85,
    'summary': 'Izin modulu icin yeni gelistirmeler',
    'website': 'https://volkansendag.com',
    'description': """
Izin modulu icin yeni gelistirmeler.
=====================================

Yapilacak calismalar
* Izin onayini mail olarak gondermek.

""",
    'depends': ['hr', 'resource'],
    'data': [
        'security/hr_leave_improve_security.xml',
        'views/hr_leave_improve_view.xml',
        'views/hr_leave_improve_reports.xml',
        'views/hr_leave_improve_mail.xml'
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
