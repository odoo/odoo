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
        "name":"Server Object Synchronization",
        "version":"0.1",
        "author":"OpenERP SA",
        "category":"Tools",
        "description": """
Synchronization with all objects.
=================================
        """,
        "depends":["base"],
        "demo_xml":[],
        "update_xml":[ "wizard/base_synchro_view.xml",
                      "base_synchro_view.xml",
                       "security/ir.model.access.csv",],
        "active":False,
        "installable":True,
        "certificate" : "00925429283944551453",
        'images': ['images/1_servers_synchro.jpeg','images/2_synchronize.jpeg','images/3_objects_synchro.jpeg',],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
