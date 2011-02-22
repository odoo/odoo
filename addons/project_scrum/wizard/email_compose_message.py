# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from osv import osv
from osv import fields
from tools.translate import _

class email_compose_message(osv.osv_memory):
    _inherit = 'email.compose.message'

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        result = super(email_compose_message, self).default_get(cr, uid, fields, context=context)

        if context.get('active_id',False) and context.get('active_model',False) and context.get('active_model') == 'project.scrum.meeting':

            meeting_pool = self.pool.get('project.scrum.meeting')
            user_pool = self.pool.get('res.users')
            meeting = meeting_pool.browse(cr, uid, context.get('active_id'), context=context)
            sprint = meeting.sprint_id

            if 'email_from' in fields:
                user_data = user_pool.browse(cr, uid, uid, context=context)
                result.update({'email_from': user_data.address_id and user_data.address_id.email or False})

            if 'email_to' in fields and sprint.scrum_master_id and sprint.scrum_master_id.user_email:
                result.update({'email_to': sprint.scrum_master_id.user_email})

            if sprint.product_owner_id and sprint.product_owner_id.user_email:
                result.update({'email_to': result.get('email_to',False) and result.get('email_to') + ',' +  sprint.product_owner_id.user_email or sprint.product_owner_id.user_email})

            if 'name' in fields:
                subject = _("Scrum Meeting : %s") %(meeting.date)
                result.update({'name': subject})

            if 'description' in fields:
                message = _("Hello  , \nI am sending you Scrum Meeting : %s for the Sprint  '%s' of Project '%s'") %(meeting.date, sprint.name, sprint.project_id.name)
                result.update({'description': message})

            if 'model' in fields:
                result.update({'model':context.get('active_model')})

            if 'res_id' in fields:
                result.update({'res_id':context.get('active_id')})

        return result

email_compose_message()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
