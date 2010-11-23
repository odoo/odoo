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


from document import nodes
from tools.safe_eval import safe_eval as eval
try:
    from tools.dict_tools import dict_filter
except ImportError:
    from document.dict_tools import dict_filter

import urllib

    
class node_acl_mixin(object):
    def _get_dav_owner(self, cr):
        return self.uuser

    def _get_dav_group(self, cr):
        return self.ugroup
        
    def _get_dav_supported_privilege_set(self, cr):
        return '' # TODO
    
    def _get_dav_current_user_privilege_set(self, cr):
        return '' # TODO

    def _get_dav_props_hlpr(self, cr, par_class, prop_model, 
                            prop_ref_field, res_id):
        """ Helper for dav properties, usable in subclasses
        
        @param par_class The parent class
        @param prop_model The name of the orm model holding the properties
        @param prop_ref_field The name of the field at prop_model pointing to us
        @param res_id the id of self in the corresponing orm table, that should
                        match prop_model.prop_ref_field
        """
        ret = par_class.get_dav_props(self, cr)
        if prop_model:
            propobj = self.context._dirobj.pool.get(prop_model)
            uid = self.context.uid
            ctx = self.context.context.copy()
            ctx.update(self.dctx)
            # Not really needed because we don't do eval here:
            # ctx.update({'uid': uid, 'dbname': self.context.dbname })
            # dict_filter(self.context.extra_ctx, ['username', 'groupname', 'webdav_path'], ctx)
            sdomain = [(prop_ref_field, '=', False),]
            if res_id:
                sdomain = ['|', (prop_ref_field, '=', res_id)] + sdomain
            prop_ids = propobj.search(cr, uid, sdomain, context=ctx)
            if prop_ids:
                ret = ret.copy()
                for pbro in propobj.browse(cr, uid, prop_ids, context=ctx):
                    ret[pbro.namespace] = ret.get(pbro.namespace, ()) + \
                        (pbro.name,)
                    # Note that we cannot have properties to conditionally appear
                    # on the context, yet.
                
        return ret

    def _get_dav_eprop_hlpr(self, cr, ns, prop,
                            par_class, prop_model, 
                            prop_ref_field, res_id):
        """ Helper for get dav eprop, usable in subclasses
        
        @param namespace the one to search for
        @param name Name to search for
        @param par_class The parent class
        @param prop_model The name of the orm model holding the properties
        @param prop_ref_field The name of the field at prop_model pointing to us
        @param res_id the id of self in the corresponing orm table, that should
                        match prop_model.prop_ref_field
        """
        ret = par_class.get_dav_eprop(self, cr, ns, prop)
        if ret is not None:
            return ret
        if prop_model:
            propobj = self.context._dirobj.pool.get(prop_model)
            uid = self.context.uid
            ctx = self.context.context.copy()
            ctx.update(self.dctx)
            ctx.update({'uid': uid, 'dbname': self.context.dbname })
            ctx['node_classname'] = "%s.%s" % (self.__class__.__module__, self.__class__.__name__)
            dict_filter(self.context.extra_ctx, ['username', 'groupname', 'webdav_path'], ctx)
            sdomain = [(prop_ref_field, '=', False),('namespace', '=', ns), ('name','=', prop)]
            if res_id:
                sdomain = ['|', (prop_ref_field, '=', res_id)] + sdomain
            prop_ids = propobj.search(cr, uid, sdomain, context=ctx)
            if prop_ids:
                pbro = propobj.browse(cr, uid, prop_ids[0], context=ctx)
                val = pbro.value
                if pbro.do_subst:
                    if val.startswith("('") and val.endswith(")"):
                        glbls = { 'urlquote': urllib.quote, }
                        val = eval(val, glbls, ctx)
                    else:
                        val = val % ctx
                return val
        return None

class node_dir(node_acl_mixin, nodes.node_dir):
    """ override node_dir and add DAV functionality
    """
    DAV_PROPS = { "DAV:": ('owner', 'group', 
                            'supported-privilege-set', 
                            'current-user-privilege-set'), 
                }
    DAV_M_NS = { "DAV:" : '_get_dav',}
    http_options = { 'DAV': ['access-control',] }

    def get_dav_resourcetype(self, cr):
        return ('collection', 'DAV:')

    def get_dav_props(self, cr):
        return self._get_dav_props_hlpr(cr, nodes.node_dir, 
                'document.webdav.dir.property', 'dir_id', self.dir_id)

    def get_dav_eprop(self, cr, ns, prop):
        return self._get_dav_eprop_hlpr(cr, ns, prop, nodes.node_dir,
                'document.webdav.dir.property', 'dir_id', self.dir_id)


class node_file(node_acl_mixin, nodes.node_file):
    DAV_PROPS = { "DAV:": ('owner', 'group', 
                            'supported-privilege-set', 
                            'current-user-privilege-set'), 
                }
    DAV_M_NS = { "DAV:" : '_get_dav',}
    http_options = { 'DAV': ['access-control', ] }
    pass

    def get_dav_resourcetype(self, cr):
        return ''

    def get_dav_props(self, cr):
        return self._get_dav_props_hlpr(cr, nodes.node_file, 
                None, 'file_id', self.file_id)
                #'document.webdav.dir.property', 'dir_id', self.dir_id)

    #def get_dav_eprop(self, cr, ns, prop):

class node_database(nodes.node_database):
    def get_dav_resourcetype(self, cr):
        return ('collection', 'DAV:')

    def get_dav_props(self, cr):
        return self._get_dav_props_hlpr(cr, nodes.node_database,
                'document.webdav.dir.property', 'dir_id', False)

    def get_dav_eprop(self, cr, ns, prop):
        return self._get_dav_eprop_hlpr(cr, nodes.node_database, ns, prop,
                'document.webdav.dir.property', 'dir_id', False)

class node_res_obj(node_acl_mixin, nodes.node_res_obj):
    DAV_PROPS = { "DAV:": ('owner', 'group', 
                            'supported-privilege-set', 
                            'current-user-privilege-set'), 
                }
    DAV_M_NS = { "DAV:" : '_get_dav',}
    http_options = { 'DAV': ['access-control',] }

    def get_dav_resourcetype(self, cr):
        return ('collection', 'DAV:')

    def get_dav_props(self, cr):
        return self._get_dav_props_hlpr(cr, nodes.node_res_obj, 
                'document.webdav.dir.property', 'dir_id', self.dir_id)

    def get_dav_eprop(self, cr, ns, prop):
        return self._get_dav_eprop_hlpr(cr, ns, prop, nodes.node_res_obj,
                'document.webdav.dir.property', 'dir_id', self.dir_id)


class node_res_dir(node_acl_mixin, nodes.node_res_dir):
    DAV_PROPS = { "DAV:": ('owner', 'group', 
                            'supported-privilege-set', 
                            'current-user-privilege-set'), 
                }
    DAV_M_NS = { "DAV:" : '_get_dav',}
    http_options = { 'DAV': ['access-control',] }
    res_obj_class = node_res_obj

    def get_dav_resourcetype(self, cr):
        return ('collection', 'DAV:')

    def get_dav_props(self, cr):
        return self._get_dav_props_hlpr(cr, nodes.node_res_dir, 
                'document.webdav.dir.property', 'dir_id', self.dir_id)

    def get_dav_eprop(self, cr, ns, prop):
        return self._get_dav_eprop_hlpr(cr, ns, prop, nodes.node_res_dir,
                'document.webdav.dir.property', 'dir_id', self.dir_id)

# Some copies, so that this module can replace 'from document import nodes'
get_node_context = nodes.get_node_context
node_context = nodes.node_context
node_class = nodes.node_class
node_descriptor = nodes.node_descriptor


#eof
