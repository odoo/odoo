# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010 Tiny SPRL (<http://tiny.be>).
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

from osv import osv, fields
import nodes
from tools import config

class document_davdir(osv.osv):
    _inherit = 'document.directory'

    _columns = {
        # Placed here just for a reference
        'dav_prop_ids': fields.one2many('document.webdav.dir.property', 'dir_id', 'DAV properties'),
        }

    def get_node_class(self, cr, uid, ids, dbro=None, dynamic=False, context=None):
        # Note: in this function, nodes come from document_webdav/nodes.py !
        if dbro is None:
            dbro = self.browse(cr, uid, ids, context=context)

        if dynamic:
            return nodes.node_res_obj
        elif dbro.type == 'directory':
            return nodes.node_dir
        elif dbro.type == 'ressource':
            return nodes.node_res_dir
        else:
            raise ValueError("Directory node for %s type", dbro.type)

    def _prepare_context(self, cr, uid, nctx, context=None):
        nctx.node_file_class = nodes.node_file
        # We can fill some more fields, but avoid any expensive function
        # that might be not worth preparing.
        nctx.extra_ctx['webdav_path'] = '/'+config.get_misc('webdav','vdir','webdav')
        usr_obj = self.pool.get('res.users')
        res = usr_obj.read(cr, uid, uid, ['login'])
        if res:
            nctx.extra_ctx['username'] = res['login']
        # TODO group
        return

    def _locate_child(self, cr, uid, root_id, uri,nparent, ncontext):
        """ try to locate the node in uri,
            Return a tuple (node_dir, remaining_path)
        """
        return (nodes.node_database(context=ncontext), uri)

document_davdir()

class dav_dir_property(osv.osv):
    """ Arbitrary WebDAV properties, attached to document.directories.
    
    Some DAV properties have to be settable at directories, depending
    on the database directory structure.
    
    Example would be the principal-URL.
    
    There _can_ be properties without a directory, which means that they
    globally apply to all the directories (aka. collections) of the
    present database.
    """
    _name = 'document.webdav.dir.property'
    
    _columns = {
        'create_date': fields.datetime('Date Created', readonly=True),
        'create_uid':  fields.many2one('res.users', 'Creator', readonly=True),
        'write_date': fields.datetime('Date Modified', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True),
        'dir_id': fields.many2one('document.directory', 'Directory', required=False, select=1),
        'namespace': fields.char('Namespace', size=127, required=True),
        'name': fields.char('Name', size=64, required=True),
        'value': fields.text('Value'),
        'do_subst': fields.boolean('Substitute', required=True),
        }
        
    _defaults = {
        'do_subst': False,
        }
        
dav_dir_property()

class dav_file_property(osv.osv):
    """ Arbitrary WebDAV properties, attached to ir.attachments.
    
    A special case is the locks that can be applied on file nodes.
    
    There _can_ be properties without a file (RFC?), which means that they
    globally apply to all the attachments of the present database.
    
    TODO access permissions, per property.
    """
    _name = 'document.webdav.file.property'
    
    _columns = {
        'create_date': fields.datetime('Date Created', readonly=True),
        'create_uid':  fields.many2one('res.users', 'Creator', readonly=True),
        'write_date': fields.datetime('Date Modified', readonly=True),
        'write_uid':  fields.many2one('res.users', 'Last Modification User', readonly=True),
        'file_id': fields.many2one('ir.attachment', 'Document', required=False, select=1),
        'namespace': fields.char('Namespace', size=127, required=True),
        'name': fields.char('Name', size=64, required=True),
        'value': fields.text('Value'),
        'do_subst': fields.boolean('Substitute', required=True),
        }
        
    _defaults = {
        'do_subst': False,
        }
        
dav_file_property()

#eof
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
