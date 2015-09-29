# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields,osv

class res_partner(osv.osv):
    """ Inherits partner and adds CRM information in the partner form """
    _inherit = 'res.partner'

    def _opportunity_meeting_count(self, cr, uid, ids, field_name, arg, context=None):
        res = dict(map(lambda x: (x,{'opportunity_count': 0, 'meeting_count': 0}), ids))
        # the user may not have access rights for opportunities or meetings
        try:
            for partner in self.browse(cr, uid, ids, context):
                if partner.is_company:
                    operator = 'child_of'
                else:
                    operator = '='
                opp_ids = self.pool['crm.lead'].search(cr, uid, [('partner_id', operator, partner.id), ('type', '=', 'opportunity'), ('probability', '<', '100')], context=context)
                res[partner.id] = {
                    'opportunity_count': len(opp_ids),
                    'meeting_count': len(partner.meeting_ids),
                }
        except:
            pass
        return res

    _columns = {
        'team_id': fields.many2one('crm.team', 'Sales Team', oldname='section_id'),
        'opportunity_ids': fields.one2many('crm.lead', 'partner_id',\
            'Opportunities', domain=[('type', '=', 'opportunity')]),
        'meeting_ids': fields.many2many('calendar.event', 'calendar_event_res_partner_rel','res_partner_id', 'calendar_event_id',
            'Meetings'),
        'opportunity_count': fields.function(_opportunity_meeting_count, string="Opportunity", type='integer', multi='opp_meet'),
        'meeting_count': fields.function(_opportunity_meeting_count, string="# Meetings", type='integer', multi='opp_meet'),
    }

    def redirect_partner_form(self, cr, uid, partner_id, context=None):
        search_view = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'view_res_partner_filter')
        value = {
            'domain': "[]",
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'res.partner',
            'res_id': int(partner_id),
            'view_id': False,
            'context': context,
            'type': 'ir.actions.act_window',
            'search_view_id': search_view and search_view[1] or False
        }
        return value

    def make_opportunity(self, cr, uid, ids, opportunity_summary, planned_revenue=0.0, probability=0.0, partner_id=None, context=None):
        lead_obj = self.pool.get('crm.lead')
        tag_ids = self.pool['crm.lead.tag'].search(cr, uid, [])
        opportunity_ids = {}
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner_id:
                partner_id = partner.id
            opportunity_id = lead_obj.create(cr, uid, {
                'name' : opportunity_summary,
                'planned_revenue' : planned_revenue,
                'probability' : probability,
                'partner_id' : partner_id,
                'tag_ids' : tag_ids and tag_ids[0] or [],
                'type': 'opportunity'
            }, context=context)
            opportunity_ids[partner_id] = opportunity_id
        return opportunity_ids

    def schedule_meeting(self, cr, uid, ids, context=None):
        partner_ids = list(ids)
        partner_ids.append(self.pool.get('res.users').browse(cr, uid, uid).partner_id.id)
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'calendar', 'action_calendar_event', context)
        res['context'] = {
            'search_default_partner_ids': context['partner_name'],
            'default_partner_ids': partner_ids,
        }
        return res
