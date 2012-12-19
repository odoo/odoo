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

from openerp.osv import fields, osv

class crm_claim_settings(osv.osv_memory):
    _name = 'sale.config.settings'
    _inherit = ['sale.config.settings', 'fetchmail.config.settings']

    _columns = {
        'fetchmail_claim': fields.boolean("Create claims from incoming mails",
            fetchmail_model='crm.claim', fetchmail_name='Incoming Claims',
            help="""Allows you to configure your incoming mail server, and create claims from incoming emails."""),
    }
