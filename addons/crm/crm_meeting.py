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


class crm_meeting(osv.osv):
    _name = 'crm.meeting'
    _description = "Meeting Cases"
    _order = "id desc"
    _inherit = ["crm.case", "calendar.event"]

    _columns = {
        'priority': fields.selection([('5','Lowest'),
                                    ('4','Low'),
                                    ('3','Normal'),
                                    ('2','High'),
                                    ('1','Highest')
                                    ], 'Priority'), 
        'categ_id': fields.many2one('crm.case.categ', 'Category', \
                            domain="[('section_id','=',section_id),\
                            ('object_id.model', '=', 'crm.meeting')]", \
            help='Category related to the section.Subdivide the CRM cases \
independently or section-wise.'), 
    }

    def msg_new(self, cr, uid, msg):
        mailgate_obj = self.pool.get('mail.gateway')
        msg_body = mailgate_obj.msg_body_get(msg)
        data = {
            'name': msg['Subject'], 
            'email_from': msg['From'], 
            'email_cc': msg['Cc'], 
            'user_id': False, 
            'description': msg_body['body'], 
            'history_line': [(0, 0, {'description': msg_body['body'], 'email': msg['From'] })], 
        }
        res = mailgate_obj.partner_get(cr, uid, msg['From'])
        if res:
            data.update(res)
        res = self.create(cr, uid, data)
        return res

crm_meeting()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
