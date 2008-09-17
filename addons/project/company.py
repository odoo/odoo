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

from osv import fields
from osv import osv

class res_company(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'project_time_mode': fields.selection(
            [('hours','Hours'),('day','Days'),('week','Weeks'),('month','Months')],
            'Project Time Unit',
            help='This will set the unit of measure used in projects and tasks.\n' \
"If you use the timesheet linked to projects (project_timesheet module), don't " \
"forget to setup the right unit of measure in your employees.",
            required=True,
        ),
    }
    _defaults = {
        'project_time_mode': lambda *args: 'hours',
    }
res_company()

