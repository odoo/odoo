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

import sys

from osv import fields, osv
import tools
from tools.translate import _

class project_gtd_timebox(osv.osv):
    _inherit = "project.gtd.timebox"
    _description = "TODO"
    _columns = {
        'name': fields.char('Title', size=128, required=True, select=1, translate=1),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of contexts."),
        'icon': fields.selection(tools.icons, 'Icon', size=64),
    }
    _defaults = {
        'sequence': 1
    }
    _order = "sequence, name"

project_gtd_timebox()




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
