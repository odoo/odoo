# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import base64

from osv import osv, fields
import urlparse

import os

import pooler
import netsvc
#import StringIO

from psycopg2 import Binary
#from tools import config
import tools
from tools.translate import _
import nodes

class document_file(osv.osv):
    _inherit = 'ir.attachment'
    _rec_name = 'datas_fname'
    def _get_filestore(self, cr):
        return os.path.join(tools.config['root_path'], 'filestore', cr.dbname)

    def _data_get(self, cr, uid, ids, name, arg, context):
        fbrl = self.browse(cr,uid,ids,context=context)
        nctx = nodes.get_node_context(cr,uid,context)
        result = {}
        bin_size = context.get('bin_size', False)
        for fbro in fbrl:
                fnode = nodes.node_file(None,None,nctx,fbro)
                if not bin_size:
                        data = fnode.get_data(cr,fbro)
                        result[fbro.id] = base64.encodestring(data or '')
                else:
                        result[fbro.id] = fnode.get_data_len(cr,fbro)
                        
        return result

    #
    # This code can be improved
    #
    def _data_set(self, cr, uid, id, name, value, arg, context):
        if not value:
            return True
        fbro = self.browse(cr,uid,id,context=context)
        nctx = nodes.get_node_context(cr,uid,context)
        fnode = nodes.node_file(None,None,nctx,fbro)
        res = fnode.set_data(cr,base64.decodestring(value),fbro)
        return res

    _columns = {
        'user_id': fields.many2one('res.users', 'Owner', select=1),
        'group_ids': fields.many2many('res.groups', 'document_directory_group_rel', 'item_id', 'group_id', 'Groups'),
        # the directory id now is mandatory. It can still be computed automatically.
        'parent_id': fields.many2one('document.directory', 'Directory', select=1, required=True),
        'file_size': fields.integer('File Size', required=True),
        'file_type': fields.char('Content Type', size=32),
        # If ir.attachment contained any data before document is installed, preserve
        # the data, don't drop the column!
        'db_datas': fields.binary('Data',oldname='datas'),
        'index_content': fields.text('Indexed Content'),
        'write_date': fields.datetime('Date Modified', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True),
        'create_date': fields.datetime('Date Created', readonly=True),
        'create_uid':  fields.many2one('res.users', 'Creator', readonly=True),
        'store_method': fields.selection([('db','Database'),('fs','Filesystem'),('link','Link')], "Storing Method"),
        'datas': fields.function(_data_get,method=True,fnct_inv=_data_set,string='File Content',type="binary", nodrop=True),
        'store_fname': fields.char('Stored Filename', size=200),
        'res_model': fields.char('Attached Model', size=64), #res_model
        'res_id': fields.integer('Attached ID'), #res_id
        'partner_id':fields.many2one('res.partner', 'Partner', select=1),
        'title': fields.char('Resource Title',size=64),
    }

    def __get_def_directory(self,cr,uid, context = None):
        dirobj = self.pool.get('document.directory')
        return dirobj._get_root_directory(cr,uid,context)

    _defaults = {
        'user_id': lambda self,cr,uid,ctx:uid,
        'file_size': lambda self,cr,uid,ctx:0,
        'store_method': lambda *args: 'db',
        'parent_id': __get_def_directory
    }
    _sql_constraints = [
        ('filename_uniq', 'unique (name,parent_id,res_id,res_model)', 'The file name must be unique !')
    ]
    def _check_duplication(self, cr, uid,vals,ids=[],op='create'):
        name=vals.get('name',False)
        parent_id=vals.get('parent_id',False)
        res_model=vals.get('res_model',False)
        res_id=vals.get('res_id',0)
        if op=='write':
            for file in self.browse(cr,uid,ids):
                if not name:
                    name=file.name
                if not parent_id:
                    parent_id=file.parent_id and file.parent_id.id or False
                if not res_model:
                    res_model=file.res_model and file.res_model or False
                if not res_id:
                    res_id=file.res_id and file.res_id or 0
                res=self.search(cr,uid,[('id','<>',file.id),('name','=',name),('parent_id','=',parent_id),('res_model','=',res_model),('res_id','=',res_id)])
                if len(res):
                    return False
        if op=='create':
            res=self.search(cr,uid,[('name','=',name),('parent_id','=',parent_id),('res_id','=',res_id),('res_model','=',res_model)])
            if len(res):
                return False
        return True
    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default ={}
        name = self.read(cr, uid, [id])[0]['name']
        default.update({'name': name+ " (copy)"})
        return super(document_file,self).copy(cr,uid,id,default,context)
    def write(self, cr, uid, ids, vals, context=None):
        res=self.search(cr,uid,[('id','in',ids)])
        if not len(res):
            return False
        if not self._check_duplication(cr,uid,vals,ids,'write'):
            raise except_orm(_('ValidateError'), _('File name must be unique!'))
        result = super(document_file,self).write(cr,uid,ids,vals,context=context)
        cr.commit()
        return result

    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        vals['title']=vals['name']
        vals['parent_id'] = context.get('parent_id',False) or vals.get('parent_id',False)
        if not vals.get('res_id', False) and context.get('default_res_id',False):
            vals['res_id']=context.get('default_res_id',False)
        if not vals.get('res_model', False) and context.get('default_res_model',False):
            vals['res_model']=context.get('default_res_model',False)
        if vals.get('res_id', False) and vals.get('res_model',False):
            obj_model=self.pool.get(vals['res_model'])
            result = obj_model.read(cr, uid, [vals['res_id']], context=context)
            if len(result):
                obj=result[0]
                if obj.get('name',False):
                    vals['title'] = (obj.get('name',''))[:60]
                if obj_model._name=='res.partner':
                    vals['partner_id']=obj['id']
                elif obj.get('address_id',False):
                    if isinstance(obj['address_id'],tuple) or isinstance(obj['address_id'],list):
                        address_id=obj['address_id'][0]
                    else:
                        address_id=obj['address_id']
                    address=self.pool.get('res.partner.address').read(cr,uid,[address_id],context=context)
                    if len(address):
                        vals['partner_id']=address[0]['partner_id'][0] or False
                elif obj.get('partner_id',False):
                    if isinstance(obj['partner_id'],tuple) or isinstance(obj['partner_id'],list):
                        vals['partner_id']=obj['partner_id'][0]
                    else:
                        vals['partner_id']=obj['partner_id']

        datas=None
        if vals.get('link',False) :
            import urllib
            datas=base64.encodestring(urllib.urlopen(vals['link']).read())
        else:
            datas=vals.get('datas',False)
        vals['file_size']= datas and len(datas) or 0
        if not self._check_duplication(cr,uid,vals):
            raise except_orm(_('ValidateError'), _('File name must be unique!'))
        result = super(document_file,self).create(cr, uid, vals, context)
        cr.commit()
        return result

    def unlink(self,cr, uid, ids, context={}):
        stor = self.pool.get('document.storage')
        unres= []
        # We have to do the unlink in 2 stages: prepare a list of actual
        # files to be unlinked, update the db (safer to do first, can be
        # rolled back) and then unlink the files. The list wouldn't exist
        # after we discard the objects
        
        for f in self.browse(cr, uid, ids, context):
            # TODO: update the node cache
            r = stor.prepare_unlink(cr,uid,f.parent_id.storage_id, f)
            if r:
                unres.append(r)
        res = super(document_file, self).unlink(cr, uid, ids, context)
        stor.do_unlink(cr,uid,unres)
        return res
        
document_file()

