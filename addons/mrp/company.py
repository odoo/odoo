##############################################################################
#
# Copyright (c) 2005-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id:
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

from osv import osv,fields

class company(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'schedule_range': fields.float('Scheduler Range', required=True,
            help="This is the time frame analysed by the scheduler when "\
            "computing procurements. All procurement that are not between "\
            "today and today+range are skipped for futur computation."),
        'po_lead': fields.float('Purchase Lead Time', required=True,
            help="This is the leads/security time for each purchase order."),
        'security_lead': fields.float('Security Days', required=True,
            help="This is the days added to what you promise to customers "\
            "for security purpose"),
        'manufacturing_lead': fields.float('Manufacturity Lead Time', required=True,
            help="Security days for each manufacturing operation."),
    }
    _defaults = {
        'schedule_range': lambda *a: 80.0,
        'po_lead': lambda *a: 1.0,
        'security_lead': lambda *a: 5.0,
        'manufacturing_lead': lambda *a: 1.0,
    }
company()


