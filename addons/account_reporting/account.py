# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: account.py 1005 2005-07-25 08:41:42Z nicoe $
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
import time
import netsvc
from osv import fields, osv

from tools.misc import currency

import mx.DateTime
from mx.DateTime import RelativeDateTime, now, DateTime, localtime


class color_rml(osv.osv):
    _name = "color.rml"
    _description = "Rml Colors"
    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'code': fields.char('code',size=64,required=True),
        }

color_rml()

class account_report_bs(osv.osv):
    _name = "account.report.bs"
    _description = "Account reporting for Balance Sheet"
    _font = [
             ('',''),
             ('Courier','Courier'),
             ('Courier-Bold','Courier-Bold'),
             ('Courier-BoldOblique','Courier-BoldOblique'),
             ('Courier-Oblique','Courier-Oblique'),
             ('Helvetica','Helvetica'),
             ('Helvetica-Bold','Helvetica-Bold'),
             ('Helvetica-Oblique','Helvetica-Oblique'),
             ('Times-Bold','Times-Bold'),
             ('Times-BoldItalic','Times-BoldItalic'),
             ('Times-Italic','Times-Italic'),
             ('Times-Roman','Times-Roman'),
            ]
    _color = [
            ('', ''),
            ('green','Green'),
            ('red','Red'),
            ('pink','Pink'),
            ('blue','Blue'),
            ('yellow','Yellow'),
            ('cyan','Cyan'),
            ('lightblue','Light Blue'),
            ('orange','Orange'),
            ]
    _style = [
            ('', ''),
            ('h1','Header 1'),
            ('h2','Header 2'),
            ('h3','Header 3'),
            ]

    def onchange_parent_id(self, cr, uid, ids, parent_id):
        v={}
        if parent_id:
            acc=self.pool.get('account.report.report').browse(cr,uid,parent_id)
            v['type']=acc.type
            if int(acc.style) < 6:
                v['style'] = str(int(acc.style)+1)
        return {'value': v}

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'sequence': fields.integer('Sequence'),
        'code': fields.char('Code', size=64, required=True),
        'account_id': fields.many2many('account.account', 'account_report_rel', 'report_id', 'account_id', 'Accounts'),
        'note': fields.text('Note'),
#       'style': fields.selection(_style, 'Style'),
        'color_font' : fields.many2one('color.rml','Font Color'),
        'color_back' : fields.many2one('color.rml','Back Color'),
        'font_style' : fields.selection(_font, 'Font'),
        'parent_id': fields.many2one('account.report.bs', 'Parent'),
        'child_id': fields.one2many('account.report.bs', 'parent_id', 'Childs'),
        'report_type' : fields.selection([('only_obj', 'Report Objects Only'),('with_account', 'Report Objects With Accounts'),('acc_with_child', 'Report Objects With Accounts and child of Accounts')],"Report Type")
    }
    _defaults = {
        'report_type': lambda *a :'only_obj'
    }

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        if not args:
            args=[]
        if not context:
            context={}
        ids = []
        if name:
            ids = self.search(cr, user, [('code','=',name)]+ args, limit=limit, context=context)
            if not ids:
                ids = self.search(cr, user, [('name',operator,name)]+ args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context=context)

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The code of the report entry must be unique !')
    ]

account_report_bs()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

