# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2015 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'Screen Driver',
    'version': '1.0',
    'category': 'Hardware Drivers',
    'sequence': 6,
    'summary': 'Provides support for customer facing displays',
    'website': 'https://www.odoo.com/page/point-of-sale',
    'description': """
Screen Driver
=============

This module allows the POS client to send rendered HTML to a remotely
installed screen. This module then displays this HTML using a web
browser.
""",
    'author': 'OpenERP SA',
    'depends': ['hw_proxy'],
    'installable': False,
    'auto_install': False,
}
