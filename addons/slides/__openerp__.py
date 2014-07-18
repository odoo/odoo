# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Odoo Slides',
    'version': '1.0',
    'summary': 'Publish Slides and Documents Online',
    'category': 'website',
    'description': """
Publish Documents as a Slides online
==============================================
You can link and publish documents and slides to the event and talks also you can publish documents and slides on slides. You can publish following all the file formats

* Publish Slides (odp, pdf)
* Publish Documents (pdf)
""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['website', 'document'],
    'data': [
        'view/slides.xml',       
    ],   
    'installable': True,
    'auto_install': False,   
}