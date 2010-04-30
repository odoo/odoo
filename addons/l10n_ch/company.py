# -*- encoding: utf-8 -*-
#
#  company.py
#  l10n_ch
#
#  Created by Nicolas Bessi based on Credric Krier contribution
#
#  Copyright (c) 2010 CamptoCamp. All rights reserved.
##############################################################################
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

from osv import fields, osv
class ResCompany(osv.osv):
    """override company in order to add bvr vertical and 
    Horizontal print delta"""
    _inherit = "res.company"
    _columns = {
        ### horiz. delta in mm 1.2 will print the bvz 1.2mm lefter
        'bvr_delta_horz': fields.float('BVR Horz. Delta (mm)',
            help='horiz. delta in mm 1.2 will print the bvz 1.2mm lefter'),
        ### vert. delta in mm 1.2 will print the bvz 1.2mm lefter
        'bvr_delta_vert': fields.float('BVR Vert. Delta (mm)',
            help='vert. delta in mm 1.2 will print the bvz 1.2mm lefter'),
    }
ResCompany()

