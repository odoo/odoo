# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com) 
# All Right Reserved
#
# Author : Nicolas Bessi (Camptocamp)
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
    """Override company to add Header object link a company can have many header and logos"""

    _inherit = "res.company"
    _columns = {
                'header_image' : fields.many2many(
                                                    'ir.header_img',
                                                    'company_img_rel',
                                                    'company_id',
                                                    'img_id',
                                                    'Available Images',
                                                ),
                'header_webkit' : fields.many2many(
                                                    'ir.header_webkit',
                                                    'company_html_rel',
                                                    'company_id',
                                                    'html_id',
                                                    'Available html',
                                                ),
                'lib_path' : fields.char('Webkit Executable Path', size=264,
                                         help="Full path to the wkhtmltopdf executable file. "
                                              "Version 0.9.9 is required. Install a static version "
                                              "of the library if you experience missing header/footers "
                                              "on Linux."),

    }
ResCompany()
