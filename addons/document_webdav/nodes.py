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
import time
import urllib
import uuid
from openerp import SUPERUSER_ID

try:
    from tools.dict_tools import dict_filter
except ImportError:
    from document.dict_tools import dict_filter

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

    def _dav_lock_hlpr(self, cr, lock_data, par_class, prop_model,
                            prop_ref_field, res_id):
        """ Helper, which uses the dav properties table for placing locks
        
        @param lock_data a dictionary of input to this function.
        @return list of tuples, DAV:activelock _contents_ structure.
                See webdav.py:class Prop2Xml() for semantics
        
        Note: although the DAV response shall be an <activelock/>, this
        function will only return the elements inside the activelock,
        because the calling function needs to append the <lockroot/> in
        it. See webdav.py:mk_lock_response()
        
        In order to reuse code, this function can be called with 
        lock_data['unlock_mode']=True, in order to unlock.
        
        @return bool in unlock mode, (davstruct, prop_id, token) in lock/refresh,
                    or (False, prop_id, token) if already locked,
                    or (False, False, False) if lock not found to refresh
        """
        assert prop_model
        assert res_id
        assert isinstance(lock_data, dict), '%r' % lock_data
        propobj = self.context._dirobj.pool.get(prop_model)
        uid = self.context.uid
        ctx = self.context.context.copy()
        ctx.update(self.dctx)
        ctx.update({'uid': uid, 'dbname': self.context.dbname })
        ctx['node_classname'] = "%s.%s" % (self.__class__.__module__, self.__class__.__name__)
        dict_filter(self.context.extra_ctx, ['username', 'groupname', 'webdav_path'], ctx)
        sdomain = [(prop_ref_field, '=', res_id), ('namespace', '=', 'DAV:'),
                    ('name','=', 'lockdiscovery')]
        props_to_delete = []
        lock_found = False
        lock_val = None
        tmout2 = int(lock_data.get('timeout', 3*3600))
        
        prop_ids = propobj.search(cr, uid, sdomain, context=ctx)
        if prop_ids:
            for pbro in propobj.browse(cr, uid, prop_ids, context=ctx):
                val = pbro.value
                if pbro.do_subst:
                    if val.startswith("('") and val.endswith(")"):
                        glbls = { 'urlquote': urllib.quote, }
                        val = eval(val, glbls, ctx)
                    else:
                        # all locks should be at "subst" format
                        continue
                if not (val and isinstance(val, tuple) 
                        and val[0:2] == ( 'activelock','DAV:')):
                    # print "Value is not activelock:", val
                    continue
                
                old_token = False
                old_owner = False
                try:
                    # discover the timeout. If anything goes wrong, delete
                    # the lock (cleanup)
                    tmout = False
                    for parm in val[2]:
                        if parm[1] != 'DAV:':
                            continue
                        if parm[0] == 'timeout':
                            if isinstance(parm[2], basestring) \
                                    and parm[2].startswith('Second-'):
                                tmout = int(parm[2][7:])
                        elif parm[0] == 'locktoken':
                            if isinstance(parm[2], basestring):
                                old_token = parm[2]
                            elif isinstance(parm[2], tuple) and \
                                parm[2][0:2] == ('href','DAV:'):
                                    old_token = parm[2][2]
                            else:
                                # print "Mangled token in DAV property: %r" % parm[2]
                                props_to_delete.append(pbro.id)
                                continue
                        elif parm[0] == 'owner':
                            old_owner = parm[2] # not used yet
                    if tmout:
                        mdate = pbro.write_date or pbro.create_date
                        mdate = time.mktime(time.strptime(mdate,'%Y-%m-%d %H:%M:%S'))
                        if mdate + tmout < time.time():
                            props_to_delete.append(pbro.id)
                            continue
                    else:
                        props_to_delete.append(pbro.id)
                        continue
                except ValueError:
                    props_to_delete.append(pbro.id)
                    continue
                
                # A valid lock is found here
                if lock_data.get('refresh', False):
                    if old_token != lock_data.get('token'):
                        continue
                    # refresh mode. Just touch anything and the ORM will update
                    # the write uid+date, won't it?
                    # Note: we don't update the owner, because incoming refresh
                    # wouldn't have a body, anyway.
                    propobj.write(cr, uid, [pbro.id,], { 'name': 'lockdiscovery'})
                elif lock_data.get('unlock_mode', False):
                    if old_token != lock_data.get('token'):
                        continue
                    props_to_delete.append(pbro.id)
                
                lock_found = pbro.id
                lock_val = val

        if tmout2 > 3*3600: # 3 hours maximum
            tmout2 = 3*3600
        elif tmout2 < 300:
            # 5 minutes minimum, but an unlock request can always
            # break it at any time. Ensures no negative values, either.
            tmout2 = 300
        
        if props_to_delete:
            # explicitly delete, as admin, any of the ids we have identified.
            propobj.unlink(cr, SUPERUSER_ID, props_to_delete)
        
        if lock_data.get('unlock_mode', False):
            return lock_found and True
        elif (not lock_found) and not (lock_data.get('refresh', False)):
            # Create a new lock, attach and return it.
            new_token = uuid.uuid4().urn
            lock_val = ('activelock', 'DAV:', 
                    [ ('locktype', 'DAV:', (lock_data.get('locktype',False) or 'write','DAV:')),
                      ('lockscope', 'DAV:', (lock_data.get('lockscope',False) or 'exclusive','DAV:')),
                      # ? ('depth', 'DAV:', lock_data.get('depth','0') ),
                      ('timeout','DAV:', 'Second-%d' % tmout2),
                      ('locktoken', 'DAV:', ('href', 'DAV:', new_token)),
                      # ('lockroot', 'DAV: ..., we don't store that, appended by caller
                    ])
            new_owner = lock_data.get('lockowner',False) or ctx.get('username', False)
            if new_owner:
                lock_val[2].append( ('owner', 'DAV:',  new_owner) )
            prop_id = propobj.create(cr, uid, { prop_ref_field: res_id,
                    'namespace': 'DAV:', 'name': 'lockdiscovery',
                    'do_subst': True, 'value': repr(lock_val) })
            return (lock_val[2], prop_id, new_token )
        elif not lock_found: # and refresh
            return (False, False, False)
        elif lock_found and not lock_data.get('refresh', False):
            # already locked
            return (False, lock_found, old_token)
        else:
            return (lock_val[2], lock_found, old_token )

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
                            'current-user-privilege-set',
                            ), 
                }
    DAV_M_NS = { "DAV:" : '_get_dav',}
    http_options = { 'DAV': ['access-control', ] }
    pass

    def get_dav_resourcetype(self, cr):
        return ''

    def get_dav_props(self, cr):
        return self._get_dav_props_hlpr(cr, nodes.node_file, 
                'document.webdav.file.property', 'file_id', self.file_id)

    def dav_lock(self, cr, lock_data):
        """ Locks or unlocks the node, using DAV semantics.
        
        Unlocking will be done when lock_data['unlock_mode'] == True
        
        See _dav_lock_hlpr() for calling details.
        
        It is fundamentally OK to use this function from non-DAV endpoints,
        but they will all have to emulate the tuple-in-list structure of
        the DAV lock data. RFC if this translation should be done inside
        the _dav_lock_hlpr (to ease other protocols).
        """
        return self._dav_lock_hlpr(cr, lock_data, nodes.node_file, 
                'document.webdav.file.property', 'file_id', self.file_id)

    def dav_unlock(self, cr, token):
        """Releases the token lock held for the node
        
        This is a utility complement of dav_lock()
        """
        lock_data = { 'token': token, 'unlock_mode': True }
        return self._dav_lock_hlpr(cr, lock_data, nodes.node_file, 
                'document.webdav.file.property', 'file_id', self.file_id)

    def get_dav_eprop(self, cr, ns, prop):
        if ns == 'DAV:' and prop == 'supportedlock':
            return [ ('lockentry', 'DAV:', 
                        [ ('lockscope','DAV:', ('shared', 'DAV:')),
                          ('locktype','DAV:', ('write', 'DAV:')),
                        ]),
                   ('lockentry', 'DAV:', 
                        [ ('lockscope','DAV:', ('exclusive', 'DAV:')),
                          ('locktype','DAV:', ('write', 'DAV:')),
                        ] )
                   ]
        return self._get_dav_eprop_hlpr(cr, ns, prop, nodes.node_file,
                'document.webdav.file.property', 'file_id', self.file_id)

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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
