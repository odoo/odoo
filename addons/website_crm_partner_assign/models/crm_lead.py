# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from openerp import SUPERUSER_ID
from openerp.addons.base_geolocalize.models.res_partner import geo_find, geo_query_address
from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.translate import _


class res_partner_grade(osv.osv):
    _order = 'sequence'
    _name = 'res.partner.grade'
    _columns = {
        'sequence': fields.integer('Sequence'),
        'active': fields.boolean('Active'),
        'name': fields.char('Level Name'),
        'partner_weight': fields.integer('Level Weight',
            help="Gives the probability to assign a lead to this partner. (0 means no assignation.)"),
    }
    _defaults = {
        'active': lambda *args: 1,
        'partner_weight':1
    }

class res_partner_activation(osv.osv):
    _name = 'res.partner.activation'
    _order = 'sequence'

    _columns = {
        'sequence' : fields.integer('Sequence'),
        'name' : fields.char('Name', required=True),
    }


class res_partner(osv.osv):
    _inherit = "res.partner"
    _columns = {
        'partner_weight': fields.integer('Level Weight',
            help="Gives the probability to assign a lead to this partner. (0 means no assignation.)"),
        'grade_id': fields.many2one('res.partner.grade', 'Level'),
        'activation' : fields.many2one('res.partner.activation', 'Activation', select=1),
        'date_partnership' : fields.date('Partnership Date'),
        'date_review' : fields.date('Latest Partner Review'),
        'date_review_next' : fields.date('Next Partner Review'),
        # customer implementation
        'assigned_partner_id': fields.many2one(
            'res.partner', 'Implemented by',
        ),
        'implemented_partner_ids': fields.one2many(
            'res.partner', 'assigned_partner_id',
            string='Implementation References',
        ),
    }
    _defaults = {
        'partner_weight': lambda *args: 0
    }

    def onchange_grade_id(self, cr, uid, ids, grade_id, context=None):
        res = {'value' :{'partner_weight':0}}
        if grade_id:
            partner_grade = self.pool.get('res.partner.grade').browse(cr, uid, grade_id)
            res['value']['partner_weight'] = partner_grade.partner_weight
        return res


class crm_lead(osv.osv):
    _inherit = "crm.lead"
    _columns = {
        'partner_latitude': fields.float('Geo Latitude', digits=(16, 5)),
        'partner_longitude': fields.float('Geo Longitude', digits=(16, 5)),
        'partner_assigned_id': fields.many2one('res.partner', 'Assigned Partner',track_visibility='onchange' , help="Partner this case has been forwarded/assigned to.", select=True),
        'partner_declined_ids': fields.many2many(
            'res.partner',
            'crm_lead_declined_partner',
            'lead_id',
            'partner_id',
            string='Partner not interested'),
        'date_assign': fields.date('Assignation Date', help="Last date this case was forwarded/assigned to a partner"),
    }

    def _merge_data(self, cr, uid, ids, fields, context=None):
        fields += ['partner_latitude', 'partner_longitude', 'partner_assigned_id', 'date_assign']
        return super(crm_lead, self)._merge_data(cr, uid, ids, fields, context=context)

    def onchange_assign_id(self, cr, uid, ids, partner_assigned_id, context=None):
        """This function updates the "assignation date" automatically, when manually assign a partner in the geo assign tab
        """

        if not partner_assigned_id:
            return {'value':{'date_assign': False}}
        else:
            partners = self.pool.get('res.partner').browse(cr, uid, [partner_assigned_id], context=context)
            user_id = partners[0] and partners[0].user_id.id or False
            return {'value':
                        {'date_assign': fields.date.context_today(self,cr,uid,context=context),
                         'user_id' : user_id}
                   }

    def assign_salesman_of_assigned_partner(self, cr, uid, ids, context=None):
        salesmans_leads = {}
        for lead in self.browse(cr, uid, ids, context=context):
            if (lead.stage_id.probability > 0 and lead.stage_id.probability < 100) or lead.stage_id.sequence == 1: 
                if lead.partner_assigned_id and lead.partner_assigned_id.user_id and lead.partner_assigned_id.user_id != lead.user_id:
                    salesman_id = lead.partner_assigned_id.user_id.id
                    if salesmans_leads.get(salesman_id):
                        salesmans_leads[salesman_id].append(lead.id)
                    else:
                        salesmans_leads[salesman_id] = [lead.id]
        for salesman_id, lead_ids in salesmans_leads.items():
            salesteam_id = self.on_change_user(cr, uid, lead_ids, salesman_id, context=None)['value'].get('team_id')
            self.write(cr, uid, lead_ids, {'user_id': salesman_id, 'team_id': salesteam_id}, context=context)

    def action_assign_partner(self, cr, uid, ids, context=None):
        return self.assign_partner(cr, uid, ids, partner_id=False, context=context)

    def assign_partner(self, cr, uid, ids, partner_id=False, context=None):
        partner_ids = {}
        res = False
        res_partner = self.pool.get('res.partner')
        if not partner_id:
            partner_ids = self.search_geo_partner(cr, uid, ids, context=context)
        for lead in self.browse(cr, uid, ids, context=context):
            if not partner_id:
                partner_id = partner_ids.get(lead.id, False)
            if not partner_id:
                tag_to_add = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'website_crm_partner_assign', 'tag_portal_lead_partner_unavailable')[1]       
                self.write(cr, uid, [lead.id], {'tag_ids': [(4, tag_to_add, False)]}, context=context)
                continue
            self.assign_geo_localize(cr, uid, [lead.id], lead.partner_latitude, lead.partner_longitude, context=context)
            partner = res_partner.browse(cr, uid, partner_id, context=context)
            if partner.user_id:
                salesteam_id = partner.team_id and partner.team_id.id or False
                self.allocate_salesman(cr, uid, [lead.id], [partner.user_id.id], team_id=salesteam_id, context=context)
            values = {'date_assign': fields.date.context_today(self,cr,uid,context=context), 'partner_assigned_id': partner_id}
            self.write(cr, uid, [lead.id], values, context=context)
        return res

    def assign_geo_localize(self, cr, uid, ids, latitude=False, longitude=False, context=None):
        if latitude and longitude:
            self.write(cr, uid, ids, {
                'partner_latitude': latitude,
                'partner_longitude': longitude
            }, context=context)
            return True
        # Don't pass context to browse()! We need country name in english below
        for lead in self.browse(cr, uid, ids):
            if lead.partner_latitude and lead.partner_longitude:
                continue
            if lead.country_id:
                result = geo_find(geo_query_address(street=lead.street,
                                                    zip=lead.zip,
                                                    city=lead.city,
                                                    state=lead.state_id.name,
                                                    country=lead.country_id.name))
                if result:
                    self.write(cr, uid, [lead.id], {
                        'partner_latitude': result[0],
                        'partner_longitude': result[1]
                    }, context=context)
        return True

    def search_geo_partner(self, cr, uid, ids, context=None):
        res_partner = self.pool.get('res.partner')
        res_partner_ids = {}
        self.assign_geo_localize(cr, uid, ids, context=context)
        for lead in self.browse(cr, uid, ids, context=context):
            partner_ids = []
            if not lead.country_id:
                continue
            latitude = lead.partner_latitude
            longitude = lead.partner_longitude
            if latitude and longitude:
                # 1. first way: in the same country, small area
                partner_ids = res_partner.search(cr, uid, [
                    ('partner_weight', '>', 0),
                    ('partner_latitude', '>', latitude - 2), ('partner_latitude', '<', latitude + 2),
                    ('partner_longitude', '>', longitude - 1.5), ('partner_longitude', '<', longitude + 1.5),
                    ('country_id', '=', lead.country_id.id),
                    ('id', 'not in', lead.partner_declined_ids.mapped('id')),
                ], context=context)

                # 2. second way: in the same country, big area
                if not partner_ids:
                    partner_ids = res_partner.search(cr, uid, [
                        ('partner_weight', '>', 0),
                        ('partner_latitude', '>', latitude - 4), ('partner_latitude', '<', latitude + 4),
                        ('partner_longitude', '>', longitude - 3), ('partner_longitude', '<' , longitude + 3),
                        ('country_id', '=', lead.country_id.id),
                        ('id', 'not in', lead.partner_declined_ids.mapped('id')),
                    ], context=context)

                # 3. third way: in the same country, extra large area
                if not partner_ids:
                    partner_ids = res_partner.search(cr, uid, [
                        ('partner_weight','>', 0),
                        ('partner_latitude','>', latitude - 8), ('partner_latitude','<', latitude + 8),
                        ('partner_longitude','>', longitude - 8), ('partner_longitude','<', longitude + 8),
                        ('country_id', '=', lead.country_id.id),
                        ('id', 'not in', lead.partner_declined_ids.mapped('id')),
                    ], context=context)

                # 5. fifth way: anywhere in same country
                if not partner_ids:
                    # still haven't found any, let's take all partners in the country!
                    partner_ids = res_partner.search(cr, uid, [
                        ('partner_weight', '>', 0),
                        ('country_id', '=', lead.country_id.id),
                        ('id', 'not in', lead.partner_declined_ids.mapped('id')),
                    ], context=context)

                # 6. sixth way: closest partner whatsoever, just to have at least one result
                if not partner_ids:
                    # warning: point() type takes (longitude, latitude) as parameters in this order!
                    cr.execute("""SELECT id, distance
                                  FROM  (select id, (point(partner_longitude, partner_latitude) <-> point(%s,%s)) AS distance FROM res_partner
                                  WHERE active
                                        AND partner_longitude is not null
                                        AND partner_latitude is not null
                                        AND partner_weight > 0
                                        AND id not in (select partner_id from crm_lead_declined_partner where lead_id = %s)
                                        ) AS d
                                  ORDER BY distance LIMIT 1""", (longitude, latitude, lead.id))
                    res = cr.dictfetchone()
                    if res:
                        partner_ids.append(res['id'])

                total_weight = 0
                toassign = []
                for partner in res_partner.browse(cr, uid, partner_ids, context=context):
                    total_weight += partner.partner_weight
                    toassign.append( (partner.id, total_weight) )

                random.shuffle(toassign) # avoid always giving the leads to the first ones in db natural order!
                nearest_weight = random.randint(0, total_weight)
                for partner_id, weight in toassign:
                    if nearest_weight <= weight:
                        res_partner_ids[lead.id] = partner_id
                        break
        return res_partner_ids

    def partner_interested(self, cr, uid, ids, comment=False, context=None):
        self.check_access_rights(cr, uid, 'write')
        message = _('<p>I am interested by this lead.</p>')
        if comment:
            message += '<p>%s</p>' % comment
        for active_id in map(int, ids):
            self.message_post(cr, uid, active_id, body=message, subtype="mail.mt_note", context=context)
            lead = self.browse(cr, uid, active_id, context=context)
            self.convert_opportunity(cr, SUPERUSER_ID, [lead.id], lead.partner_id and lead.partner_id.id or None, context=None)

    def partner_desinterested(self, cr, uid, ids, comment=False, contacted=False, context=None):
        self.check_access_rights(cr, uid, 'write')
        ids = map(int, ids)
        if contacted:
            message = _('<p>I am not interested by this lead. I contacted the lead.</p>')
        else:
            message = _('<p>I am not interested by this lead. I have not contacted the lead.</p>')
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        partner_ids = self.pool.get('res.partner').search(
            cr, SUPERUSER_ID,
            [('id', 'child_of', user.partner_id.commercial_partner_id.id)],
            context=context)
        self.message_unsubscribe(cr, SUPERUSER_ID, ids, partner_ids, context=None)
        if comment:
            message += '<p>%s</p>' % comment
        for active_id in ids:
            self.message_post(cr, uid, active_id, body=message, subtype="mail.mt_note", context=context)
        values = {
            'partner_assigned_id': False
        }
        if partner_ids:
            values['partner_declined_ids'] = map(lambda p: (4, p, 0), partner_ids)
        self.write(cr, SUPERUSER_ID, ids, values, context=context)

    def update_lead_portal(self, cr, uid, ids, values, context=None):
        self.check_access_rights(cr, uid, 'write')
        for active_id in map(int, ids):
            lead = self.browse(cr, uid, active_id, context=context)
            if values['date_action'] == '':
                values['date_action'] = False
            if lead.next_activity_id.id != values['activity_id'] or lead.title_action != values['title_action']\
               or lead.date_action != values['date_action']:
                activity = self.pool.get('crm.activity').browse(cr, SUPERUSER_ID, [lead.next_activity_id.id], context=context)
                body_html = "<div><b>%(title)s</b>: %(next_activity)s</div>%(description)s" % {
                    'title': _('Activity Done'),
                    'next_activity': activity.name,
                    'description': lead.title_action and '<p><em>%s</em></p>' % lead.title_action or '',
                }
                self.message_post(
                    cr, uid, active_id,
                    body=body_html,
                    subject=lead.title_action,
                    subtype="mail.mt_note",
                    context=context)
            self.write(cr, uid, active_id, {
                'planned_revenue': values['planned_revenue'],
                'probability': values['probability'],
                'next_activity_id': values['activity_id'],
                'title_action': values['title_action'],
                'date_action': values['date_action'] if values['date_action'] else False,
                'priority': values['priority'],
                'date_deadline': values['date_deadline'] if values['date_deadline'] else False,
            }, context=context)
