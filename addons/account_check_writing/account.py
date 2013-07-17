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

from openerp.osv import osv,fields

class account_journal(osv.osv):
    _inherit = "account.journal"

    _columns = {
        'allow_check_writing': fields.boolean('Allow Check writing', help='Check this if the journal is to be used for writing checks.'),
        'use_preprint_check': fields.boolean('Use Preprinted Check'),
        }

account_journal()

class res_company(osv.osv):
    _inherit = "res.company"
    _columns = {
        'check_layout': fields.selection([
            ('top', 'Check on Top'),
            ('middle', 'Check in middle'),
            ('bottom', 'Check on bottom'),
            ],"Check Layout",
            help="Check on top is compatible with Quicken, QuickBooks and Microsoft Money. Check in middle is compatible with Peachtree, ACCPAC and DacEasy. Check on bottom is compatible with Peachtree, ACCPAC and DacEasy only"  ),
        }
        
    _defaults = {
        'check_layout' : lambda *a: 'top',
    }
    
res_company()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
