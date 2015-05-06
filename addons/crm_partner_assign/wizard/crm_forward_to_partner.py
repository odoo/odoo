# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError


class crm_lead_forward_to_partner(osv.TransientModel):
    """ Forward info history to partners. """
    _name = 'crm.lead.forward.to.partner'

    def _convert_to_assignation_line(self, cr, uid, lead, partner, context=None):
        lead_location = []
        partner_location = []
        if lead.country_id:
            lead_location.append(lead.country_id.name)
        if lead.city:
            lead_location.append(lead.city)
        if partner:
            if partner.country_id:
                partner_location.append(partner.country_id.name)
            if partner.city:
                partner_location.append(partner.city)
        return {'lead_id': lead.id,
                'lead_location': ", ".join(lead_location),
                'partner_assigned_id': partner and partner.id or False,
                'partner_location': ", ".join(partner_location),
                'lead_link': self.get_lead_portal_url(cr, uid, lead.id, lead.type, context=context),
                }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        lead_obj = self.pool.get('crm.lead')
        email_template_obj = self.pool.get('mail.template')
        try:
            template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'crm_partner_assign', 'email_template_lead_forward_mail')[1]
        except ValueError:
            template_id = False
        res = super(crm_lead_forward_to_partner, self).default_get(cr, uid, fields, context=context)
        active_ids = context.get('active_ids')
        default_composition_mode = context.get('default_composition_mode')
        res['assignation_lines'] = []
        if template_id:
            res['body'] = email_template_obj.get_email_template(cr, uid, template_id, 0).body_html
        if active_ids:
            lead_ids = lead_obj.browse(cr, uid, active_ids, context=context)
            if default_composition_mode == 'mass_mail':
                partner_assigned_ids = lead_obj.search_geo_partner(cr, uid, active_ids, context=context)
            else:
                partner_assigned_ids = dict((lead.id, lead.partner_assigned_id and lead.partner_assigned_id.id or False) for lead in lead_ids)
                res['partner_id'] = lead_ids[0].partner_assigned_id.id
            for lead in lead_ids:
                partner_id = partner_assigned_ids.get(lead.id) or False
                partner = False
                if partner_id:
                    partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context=context)
                res['assignation_lines'].append((0, 0, self._convert_to_assignation_line(cr, uid, lead, partner)))
        return res

    def action_forward(self, cr, uid, ids, context=None):
        lead_obj = self.pool.get('crm.lead')
        record = self.browse(cr, uid, ids[0], context=context)
        email_template_obj = self.pool.get('mail.template')
        try:
            template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'crm_partner_assign', 'email_template_lead_forward_mail')[1]
        except ValueError:
            raise UserError(_('The Forward Email Template is not in the database'))
        try:
            portal_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'group_portal')[1]
        except ValueError:
            raise UserError(_('The Portal group cannot be found'))

        local_context = context.copy()
        if not (record.forward_type == 'single'):
            no_email = set()
            for lead in record.assignation_lines:
                if lead.partner_assigned_id and not lead.partner_assigned_id.email:
                    no_email.add(lead.partner_assigned_id.name)
            if no_email:
                raise UserError(_('Set an email address for the partner(s): %s') % ", ".join(no_email))
        if record.forward_type == 'single' and not record.partner_id.email:
            raise UserError(_('Set an email address for the partner %s') % record.partner_id.name)

        partners_leads = {}
        for lead in record.assignation_lines:
            partner = record.forward_type == 'single' and record.partner_id or lead.partner_assigned_id
            lead_details = {
                'lead_link': lead.lead_link,
                'lead_id': lead.lead_id,
            }
            if partner:
                partner_leads = partners_leads.get(partner.id)
                if partner_leads:
                    partner_leads['leads'].append(lead_details)
                else:
                    partners_leads[partner.id] = {'partner': partner, 'leads': [lead_details]}
        stage_id = False
        if record.assignation_lines and record.assignation_lines[0].lead_id.type == 'lead':
            try:
                stage_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'crm_partner_assign', 'stage_portal_lead_assigned')[1]
            except ValueError:
                pass

        for partner_id, partner_leads in partners_leads.items():
            in_portal = False
            for contact in (partner.child_ids or [partner]):
                if contact.user_ids:
                    in_portal = portal_id in [g.id for g in contact.user_ids[0].groups_id]

            local_context['partner_id'] = partner_leads['partner']
            local_context['partner_leads'] = partner_leads['leads']
            local_context['partner_in_portal'] = in_portal
            email_template_obj.send_mail(cr, uid, template_id, ids[0], context=local_context)
            lead_ids = [lead['lead_id'].id for lead in partner_leads['leads']]
            values = {'partner_assigned_id': partner_id, 'user_id': partner_leads['partner'].user_id.id}
            if stage_id:
                values['stage_id'] = stage_id
            lead_obj.write(cr, uid, lead_ids, values)
            self.pool.get('crm.lead').message_subscribe(cr, uid, lead_ids, [partner_id], context=context)
        return True

    def get_lead_portal_url(self, cr, uid, lead_id, type, context=None):
        action = type == 'opportunity' and 'action_portal_opportunities' or 'action_portal_leads'
        try:
            action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'crm_partner_assign', action)[1]
        except ValueError:
            action_id = False
        portal_link = "%s/?db=%s#id=%s&action=%s&view_type=form" % (self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url'), cr.dbname, lead_id, action_id)
        return portal_link

    def get_portal_url(self, cr, uid, ids, context=None):
        portal_link = "%s/?db=%s" % (self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url'), cr.dbname)
        return portal_link

    _columns = {
        'forward_type': fields.selection([('single', 'a single partner: manual selection of partner'), ('assigned', "several partners: automatic assignation, using GPS coordinates and partner's grades"), ], 'Forward selected leads to'),
        'partner_id': fields.many2one('res.partner', 'Forward Leads To'),
        'assignation_lines': fields.one2many('crm.lead.assignation', 'forward_id', 'Partner Assignation'),
        'body': fields.html('Contents', help='Automatically sanitized HTML contents'),
    }

    _defaults = {
        'forward_type': lambda self, cr, uid, c: c.get('forward_type') or 'single',
    }


class crm_lead_assignation (osv.TransientModel):
    _name = 'crm.lead.assignation'
    _columns = {
        'forward_id': fields.many2one('crm.lead.forward.to.partner', 'Partner Assignation'),
        'lead_id': fields.many2one('crm.lead', 'Lead'),
        'lead_location': fields.char('Lead Location', size=128),
        'partner_assigned_id': fields.many2one('res.partner', 'Assigned Partner'),
        'partner_location': fields.char('Partner Location', size=128),
        'lead_link': fields.char('Lead  Single Links', size=128),
    }

    def on_change_lead_id(self, cr, uid, ids, lead_id, context=None):
        if not context:
            context = {}
        if not lead_id:
            return {'value': {'lead_location': False}}
        lead = self.pool.get('crm.lead').browse(cr, uid, lead_id, context=context)
        lead_location = []
        if lead.country_id:
            lead_location.append(lead.country_id.name)
        if lead.city:
            lead_location.append(lead.city)
        return {'value': {'lead_location': ", ".join(lead_location)}}

    def on_change_partner_assigned_id(self, cr, uid, ids, partner_assigned_id, context=None):
        if not context:
            context = {}
        if not partner_assigned_id:
            return {'value': {'lead_location': False}}
        partner = self.pool.get('res.partner').browse(cr, uid, partner_assigned_id, context=context)
        partner_location = []
        if partner.country_id:
            partner_location.append(partner.country_id.name)
        if partner.city:
            partner_location.append(partner.city)
        return {'value': {'partner_location': ", ".join(partner_location)}}
