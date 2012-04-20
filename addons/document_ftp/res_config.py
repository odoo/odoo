# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

from osv import fields, osv
from tools import config

class documnet_ftp_setting(osv.osv_memory):
    _name = 'knowledge.configuration'
    _inherit = 'knowledge.configuration'
    _columns = {
        'document_ftp_url': fields.char('Browse Documents', size=128,
            help ="""Click the url to browse the documents""", readonly=True),               
    }

    def get_default_ftp_config(self, cr, uid, fields, context=None):
        action = self.pool.get('ir.model.data').get_object(cr, uid, 'document_ftp', 'action_document_browse')
        return {'document_ftp_url': action.url}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
