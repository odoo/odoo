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

# demo script for geeting contact detail'
import sys
import getopt
import getpass
import atom
import gdata.contacts
import gdata.contacts.service
email='user name of gmail'
password='add the password'
gd_client = gdata.contacts.service.ContactsService()
gd_client.email = email
gd_client.password = password
gd_client.source = 'GoogleInc-ContactsPythonSample-1'
gd_client.ProgrammaticLogin()
feed= gd_client.GetContactsFeed()
next = feed.GetNextLink()
for i, entry in enumerate(feed.entry):
    print entry.title.text
        