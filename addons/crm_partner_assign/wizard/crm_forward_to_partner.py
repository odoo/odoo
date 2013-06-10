# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
from openerp.tools.translate import _
from urllib import urlencode
from urlparse import urljoin

class crm_lead_forward_to_partner(osv.TransientModel):
    """ Forward info history to partners. """
    _name = 'crm.lead.forward.to.partner'
    
    def get_partner(self, cr, uid, ids, context):
        lead_obj = self.pool.get('crm.lead')
        partner_id = lead_obj.search_geo_partner(cr, uid, ids, context)
        if partner_id:
            partner_id = partner_id[ids[0]]
        else:
            partner_id = False
        return partner_id
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        lead_obj = self.pool.get('crm.lead')
        email_template_obj=self.pool.get('email.template')
        base_url = self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url')
        template_id=email_template_obj.search(cr, uid,[('name','=','Lead Mass Mail'),('model_id.name','=','crm.lead.forward.to.partner')])
        res = super(crm_lead_forward_to_partner, self).default_get(cr, uid, fields, context=context)
        active_ids = context.get('active_ids')
        default_composition_mode = context.get('default_composition_mode')
        res['assignation_lines'] = []
        if template_id:
            res['body'] =  email_template_obj.get_email_template(cr, uid, template_id[0]).body_html
        if active_ids:
            leads = lead_obj.browse(cr, uid, active_ids, context=context)
            for lead in leads:
                if (not lead.partner_assigned_id) and default_composition_mode =='mass_mail':
                    partner_id=self.get_partner(cr, uid, [lead.id], context)
                    res['assignation_lines'].append({'lead_id': lead.id,
                                                     'subject': lead.name,
                                                     'city':lead.city,
                                                     'country_id':lead.country_id.id,
                                                     'partner_assigned_id': partner_id,
                                                    'lead_link':"%s/?db=%s#id=%s&model=crm.lead"%(base_url,cr.dbname,lead.id)
                                                     })
                elif default_composition_mode =='forward':
                    res['assignation_lines'].append({'lead_id': lead.id,
                                                     'subject': lead.name,
                                                     'city':lead.city,
                                                     'country_id':lead.country_id.id,
                                                     'partner_assigned_id': lead.partner_assigned_id.id,
                                                    'lead_link':"%s/?db=%s#id=%s&model=crm.lead"%(base_url,cr.dbname,lead.id)
                                                     })
                    res['partner_id']=lead.partner_assigned_id.id
        return res
    
    def action_forward(self, cr, uid, ids, context=None):
        lead_obj = self.pool.get('crm.lead')
        record = self.browse(cr, uid, ids, context=context)
        email_template_obj=self.pool.get('email.template')
        tamplate_id=email_template_obj.search(cr, uid,[('name','=','Lead Mass Mail'),('model_id.name','=','crm.lead.forward.to.partner')])
        if record[0].forward_type == "single":
            email_template_obj.send_mail(cr, uid, tamplate_id[0],ids[0])
            active_ids = context.get('active_ids')
            if active_ids:
                lead_obj.write(cr, uid, active_ids, {'partner_assigned_id': record[0].partner_id.id , 'user_id': record[0].partner_id.user_id.id})
        else:
            for lead in record[0].assignation_lines:
                self.write(cr, uid, ids, {'partner_id':lead.partner_assigned_id.id,
                                          'lead_single_link': lead.lead_link,
                                          'lead_single_id':lead.lead_id.id
                                          })
                email_template_obj.send_mail(cr, uid,tamplate_id[0],ids[0])
                lead_obj.write(cr, uid, [lead.lead_id.id], {'partner_assigned_id': lead.partner_assigned_id.id ,'user_id': lead.partner_assigned_id.user_id.id})
        return True
    
    _columns = {
        'forward_type':fields.selection([ ('single','a single partner: manual selection of partner'), ('assigned',"several partners: automatic assignation, using GPS coordinates and partner's grades"), ],'Forward selected leads to'),
        'partner_id':fields.many2one('res.partner', 'Forward Leads To'),
        'assignation_lines': fields.one2many('crm.lead.assignation', 'forward_id', 'Partner Assignation'),
        'show_mail': fields.boolean('Show the email will be sent'),
        'body': fields.html('Contents', help='Automatically sanitized HTML contents'),
        'lead_single_id':fields.many2one('crm.lead', 'Lead'),
        'lead_single_link': fields.char('Lead  Single Links',  size=128),
    }
    
    _defaults = {
        'forward_type': 'single',
    }
    
class crm_lead_assignation (osv.TransientModel):
    _name = 'crm.lead.assignation'
    _columns = {
        'forward_id':fields.many2one('crm.lead.forward.to.partner', 'Partner Assignation'),
        'lead_id':fields.many2one('crm.lead', 'Lead'),
        'subject': fields.char('Subject', size=64),
        'city': fields.char('City', size=128),
        'country_id': fields.many2one('res.country', 'Country'),
        'partner_assigned_id': fields.many2one('res.partner', 'Assigned Partner'),
        'lead_link': fields.char('Lead  Single Links',  size=128),
    }
# # vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
