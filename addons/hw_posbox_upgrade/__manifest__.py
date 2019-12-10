# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'IoTBox Software Upgrader',
    'category': 'Sales/Point Of Sale',
    'website': 'https://www.odoo.com/page/point-of-sale-hardware',
    'sequence': 6,
    'summary': 'Remotely upgrade the IoTBox software',
    'description': """
IoTBox Software Upgrader
========================

This module allows to remotely upgrade the IoTBox software to a
new version. This module is specific to the IoTBox setup and environment
and should not be installed on regular Odoo servers.

""",
    'depends': ['hw_proxy'],
    'installable':  False,
}
