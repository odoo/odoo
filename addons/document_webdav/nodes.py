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

class node_acl_mixin(object):
    def _get_dav_owner(self, cr):
        return self.uuser

    def _get_dav_group(self, cr):
        return self.ugroup
        
    def _get_dav_supported_privilege_set(self, cr):
        return '' # TODO
    
    def _get_dav_current_user_privilege_set(self, cr):
        return '' # TODO

class node_dir(node_acl_mixin, nodes.node_dir):
    DAV_PROPS = { "DAV:": ('owner', 'group', 
                            'supported-privilege-set', 
                            'current-user-privilege-set'), 
                }
    DAV_M_NS = { "DAV:" : '_get_dav',}
    http_options = { 'DAV': ['access-control',] }


class node_file(node_acl_mixin, nodes.node_file):
    DAV_PROPS = { "DAV:": ('owner', 'group', 
                            'supported-privilege-set', 
                            'current-user-privilege-set'), 
                }
    DAV_M_NS = { "DAV:" : '_get_dav',}
    http_options = { 'DAV': ['access-control', ] }
    pass


#eof
