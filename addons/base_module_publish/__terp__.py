##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
###############################################################################
{
	"name" : "Module publisher",
	"version" : "1.0",
	"author" : "Tiny",
	"website" : "http://tinyerp.com",
	"category" : "Generic Modules/Base",
	"description": """
This module can be used by developpers to automatically publish their modules
in a few click to the following websites:
* http://TinyERP.com, section module
* http://TinyForge.org
* PyPi, The python offical repository
* http://Freshmeat.net

It adds a button "Publish module" on each module, so that you simply have
to call this button when you want to release a new version of your module.
	""",
	"depends" : ["base"],
	"init_xml" : [ ],
	"demo_xml" : [ ],
	"update_xml" : [ "base_module_publish_wizard.xml" ],
	"installable": True
}
