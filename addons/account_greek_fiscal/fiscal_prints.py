# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2008 P. Christeas. All Rights Reserved
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

from osv import osv, fields

class fiscal_print(osv.osv):
  _name = 'account.fiscalgr.print'
  _inherit = ''
  _columns = {
      'hash': fields.char('Secure hash', size=40, readonly=True,),
      'date': fields.char('Print date', size=10, readonly=True,),
      'machine_id': fields.char('Machine ID', size=12, readonly=True,),
      'day_no': fields.integer('Daily sequence', readonly=True),
      'total_no': fields.integer('Total sequence', readonly=True),
      'cups_jobid': fields.integer('Job ID', readonly=True, required=True, help="CUPS job id"),
      'job_title': fields.char('Title',size=200,required=True, readonly=True,help="Title of the CUPS job, typically the invoice reference."),
      'cups_msg': fields.text('CUPS message',help="This is the message returned by cups, if the printing fails."),
      'report': fields.many2one('ir.actions.report.xml', 'Report', required=True,readonly=True),
  }
  _defaults = {
  }

fiscal_print()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

