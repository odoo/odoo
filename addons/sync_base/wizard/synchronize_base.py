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

from osv import fields,osv
from tools.translate import _


class synchronize_base(osv.osv_memory):
    _description ='Synchronize base import contact '
    _name = "synchronize.base.contact.wizard.import"

    def _get_tools_name(self, cr, user, context):
        """
        @return the list of value of the selection field
        should be overwritten by subclasses
        """
        return []

    _columns = {
        'tools':  fields.selection(_get_tools_name, 'App to synchronize with'),
    }


    def action_synchronize(self, cr, uid, ids, context=None):
        wizard_data = self.browse(cr, uid, ids, context=context)
        return self._get_action(cr, uid, wizard_data[0].tools, context=context)


    def _get_action(self, cr, uid, tools, context=None):
        if not tools:
            raise osv.except_osv(_("Error !"),_("Select App to synchronize with."))
        return self._get_actions_dic(cr, uid, context=context)[tools]

    def _get_actions_dic(self, cr, uid, context=None):
        """
            this method should be overwritten in specialize module
            @return the dictonnaries of action
        """
        return {'none' : {'type': 'ir.actions.act_window_close' }}

synchronize_base()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
