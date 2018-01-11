# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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

import base64
import time
import urllib

from openerp import osv, tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

class base_report_sxw(osv.osv_memory):
    """Base Report sxw """
    _name = 'base.report.sxw'

    _columns = {
        'report_id': fields.many2one('ir.actions.report.xml', "Report", required=True,domain=[('report_sxw_content','<>',False)],),
    }


    def get_report(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids, context=context)[0]
        data_obj = self.pool['ir.model.data']
        id2 = data_obj._get_id(cr, uid, 'base_report_designer', 'view_base_report_file_sxw')
        report = self.pool['ir.actions.report.xml'].browse(cr, uid, data['report_id'], context=context)
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'base.report.file.sxw',
            'views': [(id2, 'form')],
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }


class base_report_file_sxw(osv.osv_memory):
    """Base Report File sxw """
    _name = 'base.report.file.sxw'

    def default_get(self, cr, uid, fields, context=None):
        """
             To get default values for the object.

             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param fields: List of fields for which we want default values
             @param context: A standard dictionary

             @return: A dictionary which of fields with values.

        """
        res = super(base_report_file_sxw, self).default_get(cr, uid, fields, context=context)
        report_id1 = self.pool['base.report.sxw'].search(cr,uid,[])
        data = self.pool['base.report.sxw'].read(cr, uid, report_id1, context=context)[0]
        report = self.pool['ir.actions.report.xml'].browse(cr, uid, data['report_id'], context=context)
        if context is None:
            context={}
        if 'report_id' in fields:
            res['report_id'] = data['report_id']
            res['file_sxw'] = base64.encodestring(report.report_sxw_content)
        return res

    _columns = {
        'report_id': fields.many2one('ir.actions.report.xml', "Report", readonly=True),
        'file_sxw':fields.binary('Your .SXW file',readonly=True),
        'file_sxw_upload':fields.binary('Your .SXW file',required=True)
    }

    def upload_report(self, cr, uid, ids, context=None):
        from base_report_designer import  openerp_sxw2rml
        import StringIO
        data=self.read(cr,uid,ids)[0]
        sxwval = StringIO.StringIO(base64.decodestring(data['file_sxw_upload']))
        fp = tools.file_open('normalized_oo2rml.xsl',subdir='addons/base_report_designer/openerp_sxw2rml')
        newrmlcontent = str(openerp_sxw2rml.sxw2rml(sxwval, xsl=fp.read()))
        report = self.pool['ir.actions.report.xml'].write(cr, uid, [data['report_id']], {
            'report_sxw_content': base64.decodestring(data['file_sxw_upload']),
            'report_rml_content': newrmlcontent
        })
        cr.commit()
        data_obj = self.pool['ir.model.data']
        id2 = data_obj._get_id(cr, uid, 'base_report_designer', 'view_base_report_file_rml')
        report = self.pool['ir.actions.report.xml'].browse(cr, uid, data['report_id'], context=context)
        if id2:
            id2 = data_obj.browse(cr, uid, id2, context=context).res_id
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'base.report.rml.save',
            'views': [(id2, 'form')],
            'view_id': False,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

class base_report_rml_save(osv.osv_memory):
    """Base Report file Save"""
    _name = 'base.report.rml.save'
    def default_get(self, cr, uid, fields, context=None):
        """
             To get default values for the object.

             @param self: The object pointer.
             @param cr: A database cursor
             @param uid: ID of the user currently logged in
             @param fields: List of fields for which we want default values
             @param context: A standard dictionary
             @return: A dictionary which of fields with values.

        """
        
        res = super(base_report_rml_save, self).default_get(cr, uid, fields, context=context)
        report_ids = self.pool['base.report.sxw'].search(cr,uid,[], context=context)

        data = self.pool['base.report.file.sxw'].read(cr, uid, report_ids, context=context)[0]
        
        report = self.pool['ir.actions.report.xml'].browse(cr, uid, data['report_id'], context=context)
        
        if 'file_rml' in fields:
            res['file_rml'] =  base64.encodestring(report.report_rml_content)
        return res

    _columns = {
        'file_rml':fields.binary('Save As'),
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
