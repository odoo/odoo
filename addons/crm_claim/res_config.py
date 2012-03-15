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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv

class project_claim_mail_configuration(osv.osv_memory):
    _inherit = 'project.config.settings'

    def get_default_claim_server(self, cr, uid, ids, context=None):
        context = {'type':'issue'}
        res = self.get_default_email_configurations(cr, uid, ids, context)

        return res

    def set_default_claim_server(self, cr, uid, ids, context=None):
        context = {'type':'claim','obj':'crm.claim'}
        res = self.set_email_configurations(cr, uid, ids, context)

project_claim_mail_configuration()