# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools import config

class document_ftp_configuration(osv.osv_memory):

    _name='document.ftp.configuration'
    _description = 'Auto Directory Configuration'
    _inherit = 'res.config'
    _rec_name = 'host'
    _columns = {
        'host': fields.char('Address', size=64,
                            help="Server address or IP and port to which users should connect to for DMS access",
                            required=True),
    }

    _defaults = {
        'host': config.get('ftp_server_host', 'localhost') + ':' + config.get('ftp_server_port', '8021'),
    }

    def execute(self, cr, uid, ids, context=None):
        conf = self.browse(cr, uid, ids[0], context=context)
        data_pool = self.pool.get('ir.model.data')
        # Update the action for FTP browse.
        aid = data_pool._get_id(cr, uid, 'document_ftp', 'action_document_browse')
        aid = data_pool.browse(cr, uid, aid, context=context).res_id
        self.pool.get('ir.actions.act_url').write(cr, uid, [aid], 
                {'url': 'ftp://'+(conf.host or 'localhost:8021')+'/' + cr.dbname+'/'})

document_ftp_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
