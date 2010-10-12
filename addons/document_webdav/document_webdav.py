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

class document_davdir(osv.osv):
    _inherit = 'document.directory'

    def get_node_class(self, cr, uid, ids, dbro=None, context=None):
        # Note: in this function, nodes come from document_webdav/nodes.py !
        if dbro is None:
            dbro = self.browse(cr, uid, ids, context=context)

        if dbro.type == 'directory':
            return nodes.node_dir
        elif dbro.type == 'ressource':
            assert not dbro.ressource_parent_type_id, \
                "resource and parent_id at #%d: %r" % (dbro.id, dbro.ressource_parent_type_id)
            return nodes.node_res_dir
        else:
            raise ValueError("dir node for %s type", dbro.type)

    def _prepare_context(self, cr, uid, nctx, context):
        nctx.node_file_class = nodes.node_file
        return

document_davdir()
#eof