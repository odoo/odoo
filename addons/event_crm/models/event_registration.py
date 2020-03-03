# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    lead_ids = fields.Many2many('crm.lead', string='Leads', readonly=True, copy=False,
        help="Leads generated from the registration.")
    lead_count = fields.Integer('# Leads', compute='_compute_lead_count',
        help="Counter for the leads linked to this registration")

    @api.depends('lead_ids')
    def _compute_lead_count(self):
        for record in self:
            record.lead_count = len(record.lead_ids)

    @api.model_create_multi
    def create(self, vals_list):
        registrations = super(EventRegistration, self).create(vals_list)
        self.env['event.lead.rule'].search([]).sudo()._create_leads(registrations)
        return registrations

    def write(self, vals):
        """
        Update the lead values depending on the field that are updated in the registrations.
        There are 2 possibles cases: the first is when we update the partner_id of multiple registrations, it happens when
        a public user fill his information when he register in an event.
        The second is when we update specific values of one registration.
        Then we only get the old_registration_vals of particular fields when there is only one registration that is updated.
        """
        old_registration_vals = self._get_lead_specific_vals()
        if len(self) == 1:
            old_registration_vals.update({
                'name': self.name,
                'email': self.email,
                'phone': self.phone,
            })

        registration = super(EventRegistration, self).write(vals)

        # update leads of the registrations that are updated
        for reg in self:
            reg._update_lead_values(vals, old_registration_vals)

        return registration

    def _get_lead_values(self, rule):
        registration_lead_values = {
            'user_id': rule.lead_user_id.id,
            'type': rule.lead_type,
            'team_id': rule.lead_sales_team_id.id,
            'tag_ids': rule.lead_tag_ids.ids,
            'event_lead_rule_id': rule.id,
            'event_id': self.event_id.id,
            'referred': self.event_id.name,
            'registration_ids': self.ids,
        }
        if self.partner_id and self.partner_id != self.env.ref('base.public_partner'):
            registration_lead_values.update({
                'name': "%s - %s" % (self.event_id.name, self.partner_id.name),
                'partner_id': self.partner_id.id,
            })
        else:
            registration_lead_values.update({
                'name': "%s - %s" % (self.event_id.name, self[0].name),
                'contact_name': self[0].name,
                'email_from': self[0].email,
                'phone': self[0].phone,
                'mobile': self[0].mobile,
            })
        description = _("Participant:\n") if rule.lead_creation_basis == 'attendee' else _("Other Participants:\n")
        for prefix, registration in enumerate(self):
            description += registration._get_lead_description(prefix + 1)
        registration_lead_values.update({
            'description': description,
        })
        return registration_lead_values

    def _get_lead_description(self, prefix):
        """
        Build the description for the lead when a rule matchs for registrations using a 
        prefix for all generated lines. For example to enumerate participants or
        inform of an update in the information of a participant.
        """
        info_registration = [self.email] if self.email else []
        info_registration += [self.phone] if self.phone else []
        return "\n%s. [%s] %s (%s)\n" % (prefix, self.event_ticket_id.name, self.name, " - ".join(info_registration))

    def _update_lead_values(self, vals, old_registration_vals):
        # get fields that are updated
        lead_update_fields = [key for key, value in vals.items() if old_registration_vals.get(key) and old_registration_vals.get(key) != value]
        # build new lead values
        lead_update_vals = {}
        for key in lead_update_fields:
            if key == 'email':
                lead_update_vals['email_from'] = vals.get(key)
            elif key == 'name':
                lead_update_vals['contact_name'] = vals.get(key)
            elif key not in ['registration_answer_ids', 'state']:
                lead_update_vals[key] = vals.get(key)

        if lead_update_fields:
            for lead in self.lead_ids:
                lead_values = dict(lead_update_vals)
                # recompute the description if dependent information (name, email, phone, answers) are been modified
                if any(field in lead_update_fields for field in ['name', 'email_form', 'phone', 'registration_answer_ids']):
                    lead_values.update({
                        'description': lead.description + "\n%s" % (self._get_lead_description(_("Updated registration")))
                    })

                # if registrations was created as public user, recompute the description for lead created by "per order" rule.
                if (lead.event_lead_rule_id.lead_creation_basis == 'order' and
                    lead_values.get('partner_id') and old_registration_vals.get('partner_id') == self.env.ref('base.public_partner').id):
                    description = _("Other Participants:\n")
                    for prefix, registration in enumerate(lead.registration_ids):
                        description += registration._get_lead_description(prefix + 1)
                    lead_values['description'] = description

                if lead.event_lead_rule_id.lead_creation_basis == 'order' and self.partner_id:
                    # ignore contact fields if there is already a partner_id on a lead created by an "order" rule
                    fields_ignored = ('name', 'contact_name', 'email_from', 'phone')
                    for field in fields_ignored:
                        lead_values.pop(field, None)

                lead.write(lead_values)

    def _get_lead_specific_vals(self):
        return {
            'partner_id': self.partner_id.id,
        }

    def _get_lead_group(self, rule):
        return False
