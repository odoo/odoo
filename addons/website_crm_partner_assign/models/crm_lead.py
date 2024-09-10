# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import AccessDenied, AccessError, UserError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    partner_latitude = fields.Float('Geo Latitude', digits=(10, 7))
    partner_longitude = fields.Float('Geo Longitude', digits=(10, 7))
    partner_assigned_id = fields.Many2one('res.partner', 'Assigned Partner', tracking=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", help="Partner this case has been forwarded/assigned to.", index='btree_not_null')
    partner_declined_ids = fields.Many2many(
        'res.partner',
        'crm_lead_declined_partner',
        'lead_id',
        'partner_id',
        string='Partner not interested')
    date_partner_assign = fields.Date(
        'Partner Assignment Date', compute='_compute_date_partner_assign',
        copy=True, readonly=False, store=True,
        help="Last date this case was forwarded/assigned to a partner")

    @api.depends("partner_assigned_id")
    def _compute_date_partner_assign(self):
        for lead in self:
            if not lead.partner_assigned_id:
                lead.date_partner_assign = False
            else:
                lead.date_partner_assign = fields.Date.context_today(lead)

    def _merge_get_fields(self):
        fields_list = super(CrmLead, self)._merge_get_fields()
        fields_list += ['partner_latitude', 'partner_longitude', 'partner_assigned_id', 'date_partner_assign']
        return fields_list

    def assign_salesman_of_assigned_partner(self):
        salesmans_leads = {}
        for lead in self:
            if lead.active and lead.probability < 100:
                if lead.partner_assigned_id and lead.partner_assigned_id.user_id != lead.user_id:
                    salesmans_leads.setdefault(lead.partner_assigned_id.user_id.id, []).append(lead.id)

        for salesman_id, leads_ids in salesmans_leads.items():
            leads = self.browse(leads_ids)
            leads.write({'user_id': salesman_id})

    def action_assign_partner(self):
        """ While assigning a partner, geo-localization is performed only for leads having country
            set (see method 'assign_geo_localize' and 'search_geo_partner'). So for leads that does not
            have country set, we show the notification, and for the rest, we geo-localize them.
        """
        leads_with_country = self.filtered(lambda lead: lead.country_id)
        leads_without_country = self - leads_with_country
        if leads_without_country:
            self.env.user._bus_send('simple_notification', {
                'type': 'danger',
                'title': _("Warning"),
                'message': _('There is no country set in addresses for %(lead_names)s.', lead_names=', '.join(leads_without_country.mapped('name'))),
            })
        return leads_with_country.assign_partner(partner_id=False)

    def assign_partner(self, partner_id=False):
        partner_dict = {}
        res = False
        if not partner_id:
            partner_dict = self.search_geo_partner()
        for lead in self:
            if not partner_id:
                partner_id = partner_dict.get(lead.id, False)
            if not partner_id:
                tag_to_add = self.env.ref('website_crm_partner_assign.tag_portal_lead_partner_unavailable', raise_if_not_found=False)
                if tag_to_add:
                    lead.write({'tag_ids': [(4, tag_to_add.id, False)]})
                continue
            lead.assign_geo_localize(lead.partner_latitude, lead.partner_longitude)
            partner = self.env['res.partner'].browse(partner_id)
            if partner.user_id:
                lead._handle_salesmen_assignment(user_ids=partner.user_id.ids)
            lead.write({'partner_assigned_id': partner_id})
        return res

    def assign_geo_localize(self, latitude=False, longitude=False):
        if latitude and longitude:
            self.write({
                'partner_latitude': latitude,
                'partner_longitude': longitude
            })
            return True
        # Don't pass context to browse()! We need country name in english below
        for lead in self:
            if lead.partner_latitude and lead.partner_longitude:
                continue
            if lead.country_id:
                result = self.env['res.partner']._geo_localize(
                    lead.street, lead.zip, lead.city,
                    lead.state_id.name, lead.country_id.name
                )
                if result:
                    lead.write({
                        'partner_latitude': result[0],
                        'partner_longitude': result[1]
                    })
        return True

    def _prepare_customer_values(self, partner_name, is_company=False, parent_id=False):
        res = super()._prepare_customer_values(partner_name, is_company=is_company, parent_id=parent_id)
        res.update({
            'partner_latitude': self.partner_latitude,
            'partner_longitude': self.partner_longitude,
        })
        return res

    def search_geo_partner(self):
        Partner = self.env['res.partner']
        res_partner_ids = {}
        self.assign_geo_localize()
        for lead in self:
            partner_ids = []
            if not lead.country_id:
                continue
            latitude = lead.partner_latitude
            longitude = lead.partner_longitude
            if latitude and longitude:
                # 1. first way: in the same country, small area
                partner_ids = Partner.search([
                    ('partner_weight', '>', 0),
                    ('partner_latitude', '>', latitude - 2), ('partner_latitude', '<', latitude + 2),
                    ('partner_longitude', '>', longitude - 1.5), ('partner_longitude', '<', longitude + 1.5),
                    ('country_id', '=', lead.country_id.id),
                    ('id', 'not in', lead.partner_declined_ids.mapped('id')),
                ])

                # 2. second way: in the same country, big area
                if not partner_ids:
                    partner_ids = Partner.search([
                        ('partner_weight', '>', 0),
                        ('partner_latitude', '>', latitude - 4), ('partner_latitude', '<', latitude + 4),
                        ('partner_longitude', '>', longitude - 3), ('partner_longitude', '<', longitude + 3),
                        ('country_id', '=', lead.country_id.id),
                        ('id', 'not in', lead.partner_declined_ids.mapped('id')),
                    ])

                # 3. third way: in the same country, extra large area
                if not partner_ids:
                    partner_ids = Partner.search([
                        ('partner_weight', '>', 0),
                        ('partner_latitude', '>', latitude - 8), ('partner_latitude', '<', latitude + 8),
                        ('partner_longitude', '>', longitude - 8), ('partner_longitude', '<', longitude + 8),
                        ('country_id', '=', lead.country_id.id),
                        ('id', 'not in', lead.partner_declined_ids.mapped('id')),
                    ])

                # 5. fifth way: anywhere in same country
                if not partner_ids:
                    # still haven't found any, let's take all partners in the country!
                    partner_ids = Partner.search([
                        ('partner_weight', '>', 0),
                        ('country_id', '=', lead.country_id.id),
                        ('id', 'not in', lead.partner_declined_ids.mapped('id')),
                    ])

                # 6. sixth way: closest partner whatsoever, just to have at least one result
                if not partner_ids:
                    # warning: point() type takes (longitude, latitude) as parameters in this order!
                    self._cr.execute("""SELECT id, distance
                                  FROM  (select id, (point(partner_longitude, partner_latitude) <-> point(%s,%s)) AS distance FROM res_partner
                                  WHERE active
                                        AND partner_longitude is not null
                                        AND partner_latitude is not null
                                        AND partner_weight > 0
                                        AND id not in (select partner_id from crm_lead_declined_partner where lead_id = %s)
                                        ) AS d
                                  ORDER BY distance LIMIT 1""", (longitude, latitude, lead.id))
                    res = self._cr.dictfetchone()
                    if res:
                        partner_ids = Partner.browse([res['id']])

                if partner_ids:
                    res_partner_ids[lead.id] = random.choices(
                        partner_ids.ids,
                        partner_ids.mapped('partner_weight'),
                    )[0]

        return res_partner_ids

    def partner_interested(self, comment=False):
        message = Markup('<p>%s</p>') % _('I am interested by this lead.')
        if comment:
            message += Markup('<p>%s</p>') % comment
        for lead in self:
            lead.message_post(body=message)
            lead.sudo().convert_opportunity(lead.partner_id)  # sudo required to convert partner data

    def partner_desinterested(self, comment=False, contacted=False, spam=False):
        if contacted:
            message = Markup('<p>%s</p>') % _('I am not interested by this lead. I contacted the lead.')
        else:
            message = Markup('<p>%s</p>') % _('I am not interested by this lead. I have not contacted the lead.')
        partner_ids = self.env['res.partner'].search(
            [('id', 'child_of', self.env.user.partner_id.commercial_partner_id.id)])
        self.message_unsubscribe(partner_ids=partner_ids.ids)
        if comment:
            message += Markup('<p>%s</p>') % comment
        self.message_post(body=message)
        values = {
            'partner_assigned_id': False,
        }

        if spam:
            tag_spam = self.env.ref('website_crm_partner_assign.tag_portal_lead_is_spam', raise_if_not_found=False)
            if tag_spam and tag_spam not in self.tag_ids:
                values['tag_ids'] = [(4, tag_spam.id, False)]
        if partner_ids:
            values['partner_declined_ids'] = [(4, p, 0) for p in partner_ids.ids]
        self.sudo().write(values)

    def update_lead_portal(self, values):
        self.browse().check_access('write')
        for lead in self:
            lead_values = {
                'expected_revenue': values['expected_revenue'],
                'probability': values['probability'] or False,
                'priority': values['priority'],
                'date_deadline': values['date_deadline'] or False,
            }
            # As activities may belong to several users, only the current portal user activity
            # will be modified by the portal form. If no activity exist we create a new one instead
            # that we assign to the portal user.

            user_activity = lead.sudo().activity_ids.filtered(lambda activity: activity.user_id == self.env.user)[:1]
            if values['activity_date_deadline']:
                if user_activity:
                    user_activity.sudo().write({
                        'activity_type_id': values['activity_type_id'],
                        'summary': values['activity_summary'],
                        'date_deadline': values['activity_date_deadline'],
                    })
                else:
                    self.env['mail.activity'].sudo().create({
                        'res_model_id': self.env.ref('crm.model_crm_lead').id,
                        'res_id': lead.id,
                        'user_id': self.env.user.id,
                        'activity_type_id': values['activity_type_id'],
                        'summary': values['activity_summary'],
                        'date_deadline': values['activity_date_deadline'],
                    })
            lead.write(lead_values)

    def update_contact_details_from_portal(self, values):
        self.browse().check_access('write')
        fields = ['partner_name', 'phone', 'mobile', 'email_from', 'street', 'street2',
            'city', 'zip', 'state_id', 'country_id']
        if any([key not in fields for key in values]):
            raise UserError(_("Not allowed to update the following field(s): %s.", ", ".join([key for key in values if not key in fields])))
        return self.sudo().write(values)

    @api.model
    def create_opp_portal(self, values):
        if not (self.env.user.partner_id.grade_id or self.env.user.commercial_partner_id.grade_id):
            raise AccessDenied()
        user = self.env.user
        self = self.sudo()
        if not (values['contact_name'] and values['description'] and values['title']):
            return {
                'errors': _('All fields are required!')
            }
        tag_own = self.env.ref('website_crm_partner_assign.tag_portal_lead_own_opp', raise_if_not_found=False)
        values = {
            'contact_name': values['contact_name'],
            'name': values['title'],
            'description': values['description'],
            'priority': '2',
            'partner_assigned_id': user.commercial_partner_id.id,
        }
        if tag_own:
            values['tag_ids'] = [(4, tag_own.id, False)]

        lead = self.create(values)
        lead.assign_salesman_of_assigned_partner()
        lead.convert_opportunity(lead.partner_id)
        return {
            'id': lead.id
        }

    #
    #   DO NOT FORWARD PORT IN MASTER
    #   instead, crm.lead should implement portal.mixin
    #
    def _get_access_action(self, access_uid=None, force_website=False):
        """ Instead of the classic form view, redirect to the online document for
        portal users or if force_website=True. """
        self.ensure_one()

        user, record = self.env.user, self
        if access_uid:
            try:
                record.check_access("read")
            except AccessError:
                return super(CrmLead, self)._get_access_action(access_uid=access_uid, force_website=force_website)
            user = self.env['res.users'].sudo().browse(access_uid)
            record = self.with_user(user)
        if user.share or force_website:
            try:
                record.check_access('read')
            except AccessError:
                pass
            else:
                return {
                    'type': 'ir.actions.act_url',
                    'url': '/my/opportunity/%s' % record.id,
                }
        return super(CrmLead, self)._get_access_action(access_uid=access_uid, force_website=force_website)
