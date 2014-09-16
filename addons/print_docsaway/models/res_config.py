# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2014 OpenERP SA (<https://www.odoo.com>).
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


class print_docsaway_settings(osv.osv_memory):
    _inherit = 'base.config.settings'
    _columns = {
        'email': fields.char(string="Email"),
        'installation_key': fields.char(string="Installation Key"),
        'mode': fields.selection([('TEST', 'Test Mode'),('LIVE', 'Production Mode')], string="Mode", required=True),
        'ink': fields.selection([('BW', 'Black & White'),('CL', 'Colour')], 'Ink', required=True),
    }

    _defaults = {
        'mode': 'TEST',
        'ink': 'BW',
    }

    def get_default_print_docsaway(self, cr, uid, fields, context=None):
        email = self.pool.get("ir.config_parameter").get_param(cr, uid, "mail.docsaway.email") or ""
        installation_key = self.pool.get('ir.config_parameter').get_param(cr, uid, 'mail.docsaway.installation_key') or ""
        mode = self.pool.get('ir.config_parameter').get_param(cr, uid, 'mail.docsaway.mode') or 'TEST'
        ink = self.pool.get('ir.config_parameter').get_param(cr, uid, 'mail.docsaway.ink') or 'BW'
        return {'email': email, 'installation_key': installation_key, 'mode': mode, 'ink': ink,}

    def set_print_docsaway(self, cr, uid, ids, context=None):
        email = self.browse(cr, uid, ids[0], context)["email"] or ""
        installation_key = self.browse(cr, uid, ids[0], context)["installation_key"] or ""
        mode = self.browse(cr, uid, ids[0], context)["mode"] or ""
        ink = self.browse(cr, uid, ids[0], context)["ink"] or ""
        self.pool.get("ir.config_parameter").set_param(cr, uid, "mail.docsaway.email", email, groups=['base.group_user'])
        self.pool.get("ir.config_parameter").set_param(cr, uid, "mail.docsaway.installation_key", installation_key, groups=['base.group_user'])
        self.pool.get("ir.config_parameter").set_param(cr, uid, "mail.docsaway.mode", mode, groups=['base.group_user'])
        self.pool.get("ir.config_parameter").set_param(cr, uid, "mail.docsaway.ink", ink, groups=['base.group_user'])
