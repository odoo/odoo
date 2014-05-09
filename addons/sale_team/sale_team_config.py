# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
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


class sale_team_configuration(osv.TransientModel):
    _name = 'sale.config.settings'
    _inherit = ['sale.config.settings', 'fetchmail.config.settings']

    def set_group_multi_salesteams(self, cr, uid, ids, context=None):
        """ This method is automatically called by res_config as it begins
            with set. It is used to implement the 'one group or another'
            behavior. We have to perform some group manipulation by hand
            because in res_config.execute(), set_* methods are called
            after group_*; therefore writing on an hidden res_config file
            could not work.
            If group_multi_salesteams is checked: remove group_mono_salesteams
            from group_user, remove the users. Otherwise, just add
            group_mono_salesteams in group_user.
            The inverse logic about group_multi_salesteams is managed by the
            normal behavior of 'group_multi_salesteams' field.
        """
        def ref(xml_id):
            mod, xml = xml_id.split('.', 1)
            return self.pool['ir.model.data'].get_object(cr, uid, mod, xml, context)

        for obj in self.browse(cr, uid, ids, context=context):
            config_group = ref('base.group_mono_salesteams')
            base_group = ref('base.group_user')
            if obj.group_multi_salesteams:
                base_group.write({'implied_ids': [(3, config_group.id)]})
                config_group.write({'users': [(3, u.id) for u in base_group.users]})
            else:
                base_group.write({'implied_ids': [(4, config_group.id)]})
        return True

    _columns = {
        'group_multi_salesteams': fields.boolean("Organize Sales activities into multiple Sales Teams",
            implied_group='base.group_multi_salesteams',
            help="""Allows you to use Sales Teams to manage your leads and opportunities."""),
    }

    def _get_group_multi_salesteams(self, cr, uid, ids, context=None):
        pass
        # Todo: return the current state for the group_multi_salesteams field

    _defaults = {
        'group_multi_salesteams': _get_group_multi_salesteams
    }

