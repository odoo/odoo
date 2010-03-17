# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv

class wiki_wiki_help_open(osv.osv_memory):
    """ Basic Wiki Editing """
    _name = "wiki.wiki.help.open"
    _description = "Basic Wiki Editing"

    def open_wiki_page(self, cr, uid, ids, context):

        """ Opens Wiki Page for Editing
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of wiki page’s IDs

        """
        pages = self.pool.get('wiki.wiki').search(cr, uid, [('name', '=', 'Basic Wiki Editing')])

        value = {
            'view_type': 'form', 
            'view_mode': 'form,tree', 
            'res_model': 'wiki.wiki', 
            'view_id': False, 
            'res_id': pages[0], 
            'type': 'ir.actions.act_window', 
        }

        return value

wiki_wiki_help_open()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

