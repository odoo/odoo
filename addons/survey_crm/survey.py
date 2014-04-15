# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP S.A (<http://www.openerp.com>).
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

from openerp.osv import osv


class survey_mail_compose_message(osv.TransientModel):
    _inherit = 'survey.mail.compose.message'

    def default_get(self, cr, uid, fields, context=None):
        res = super(survey_mail_compose_message, self).default_get(cr, uid, fields, context=context)
        if context.get('active_model') == 'crm.lead' and context.get('active_ids'):
            partner_ids = []
            emails_list = []
            for lead in self.pool.get('crm.lead').browse(cr, uid, context.get('active_ids'), context=context):
                if lead.partner_id:
                    partner_ids.append(lead.partner_id.id)
                else:
                    email = lead.contact_name and "%s <%s>" % (lead.contact_name, lead.email_from or "") or lead.email_from or None
                    if email and email not in emails_list:
                        emails_list.append(email)
            multi_email = "\n".join(emails_list)

            res.update({'partner_ids': list(set(partner_ids)), 'multi_email': multi_email})
        return res
