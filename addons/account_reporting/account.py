# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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
        'child_id': fields.one2many('account.report.bs', 'parent_id', 'Children'),
        'report_type' : fields.selection([('only_obj', 'Report Objects Only'),('with_account', 'Report Objects With Accounts'),('acc_with_child', 'Report Objects With Accounts and child of Accounts')],"Report Type")
    }
    _defaults = {
        'report_type': lambda *a :'only_obj',
        'color_font': lambda *a :'',
        'color_back': lambda *a :'',
        'font_style': lambda *a :'',
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

account_report_bs()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

