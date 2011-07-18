# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    "name" : "Miscellaneous Tools",
    "version" : "1.0",
    "depends" : ["base", "base_setup"],
    "author" : "OpenERP SA",
    "category" : "Tools",
    'complexity': "easy",
    "description": """
Installer for extra tools like lunch, survey, idea, share, etc.
===============================================================

Makes the Extra Tools Configuration available from where you can install
modules like share, lunch, pad, idea, survey and subscription.
    """,
    'website': 'http://www.openerp.com',
    'init_xml': [],
    'update_xml': [
        'misc_tools_installer.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate' : '00557100228403879621',
    'images': ['images/config_extra_tools.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
