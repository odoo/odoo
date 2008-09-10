# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
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
#
##############################################################################

import xmlrpclib

sock = xmlrpclib.ServerProxy('http://localhost:8069/xmlrpc/wizard')
wiz_id = sock.create('trunk', 1, 'admin', 'mrp.procurement.compute.all')
sock.execute('trunk', 1, 'admin', wiz_id, {'form': {'po_cycle': 1.0, 'po_lead': 1.0, 'user_id': 3, 'schedule_cycle': 1.0, 'picking_lead': 1.0, 'security_lead': 50.0, 'automatic': False}, 'ids': [], 'report_type': 'pdf', 'model': 'ir.ui.menu', 'id': False}, 'compute', {})


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

