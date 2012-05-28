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
    'name': 'Event Moodle',
    'version': '0.1',
    'category': 'Tools',
    'description': """
    Configure your moodle server 

With this module you are able to connect your OpenERP with a moodle plateform.
This module will create courses and students automatically in your moodle plateform to avoid wasting time.
Now you have a simple way to create training or courses with OpenERP and moodle


STEPS TO CONFIGURE
------------------

1. activate web service in moodle
----------------------------------
>site administration >plugins>web sevices >manage protocols 
activate the xmlrpc web service 


>site administration >plugins>web sevices >manage tokens
create a token 


>site administration >plugins>web sevices >overview
activate webservice


2. Create confirmation email with login and password
----------------------------------------------------
we strongly suggest you to add those following lines at the bottom of your event confirmation email to communicate the login/password of moodle to your subscribers.


........your configuration text.......

URL: your moodle link for exemple: http://openerp.moodle.com
LOGIN: ${object.moodle_username}
PASSWORD: ${object.moodle_user_password}
""",
    'author': 'OpenERP SA',
    'depends': ['event'],
    'init_xml': [],
    'data': [
            'wizard_moodle.xml',
            'event_view.xml',
            'security/ir.model.access.csv'
            ],
    'demo_xml': [],
    'test': [],
    'installable': True,
    'auto_install': False,
    'images': ['images/token.png','images/enable_webservice.png','images/active_xmlrpc.png'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
