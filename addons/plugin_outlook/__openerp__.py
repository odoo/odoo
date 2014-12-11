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
    'name' : 'Outlook Plug-In',
    'version' : '1.0',
    'author' : 'OpenERP SA',
    'website' : 'http://www.openerp.com/',
    'depends' : ['base', 'mail','plugin'],
    'category' : 'Customer Relationship Management',
    'description': """
This module provides the Outlook Plug-in.
=========================================

Outlook plug-in allows you to select an object that you would like to add to
your email and its attachments from MS Outlook. You can select a partner, a task,
a project, an analytical account, or any other object and archive selected mail
into mail.message with attachments.
      """,
    'demo' : [],
    'data' : ['plugin_outlook.xml'],
    'auto_install': False,
    'installable': True,
    'images': ['images/config_outlook.jpeg','images/outlook_config_openerp.jpeg','images/outlook_push.jpeg'],

}
