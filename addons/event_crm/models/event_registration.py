# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from markupsafe import Markup

from odoo import api, fields, models, tools, _
from odoo.addons.phone_validation.tools import phone_validation


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    lead_ids = fields.Many2many(
        'crm.lead', string='Leads', copy=False, readonly=True,
        groups='sales_team.group_sale_salesman')
    lead_count = fields.Integer(
        '# Leads', compute='_compute_lead_count', compute_sudo=True)

    @api.depends('lead_ids')
    def _compute_lead_count(self):
        for record in self:
            record.lead_count = len(record.lead_ids)

    @api.model_create_multi
    def create(self, vals_list):
        """ Trigger rules based on registration creation, and check state for
        rules based on confirmed / done attendees. """
        registrations = super(EventRegistration, self).create(vals_list)

        # handle triggers based on creation, then those based on confirm and done
        # as registrations can be automatically confirmed, or even created directly
        # with a state given in values
        if not self.env.context.get('event_lead_rule_skip'):
            self.env['event.lead.rule'].search([('lead_creation_trigger', '=', 'create')]).sudo()._run_on_registrations(registrations)
            open_registrations = registrations.filtered(lambda reg: reg.state == 'open')
            if open_registrations:
                self.env['event.lead.rule'].search([('lead_creation_trigger', '=', 'confirm')]).sudo()._run_on_registrations(open_registrations)
            done_registrations = registrations.filtered(lambda reg: reg.state == 'done')
            if done_registrations:
                self.env['event.lead.rule'].search([('lead_creation_trigger', '=', 'done')]).sudo()._run_on_registrations(done_registrations)

        return registrations

    def write(self, vals):
        """ Update the lead values depending on fields updated in registrations.
        There are 2 main use cases

          * first is when we update the partner_id of multiple registrations. It
            happens when a public user fill its information when they register to
            an event;
          * second is when we update specific values of one registration like
            updating question answers or a contact information (email, phone);

        Also trigger rules based on confirmed and done attendees (state written
        to open and done).
        """
        to_update, event_lead_rule_skip = False, self.env.context.get('event_lead_rule_skip')
        if not event_lead_rule_skip:
            to_update = self.filtered(lambda reg: reg.lead_count)
        if to_update:
            lead_tracked_vals = to_update._get_lead_tracked_values()

        res = super(EventRegistration, self).write(vals)

        if not event_lead_rule_skip and to_update:
            self.env.flush_all()  # compute notably partner-based fields if necessary
            to_update.sudo()._update_leads(vals, lead_tracked_vals)

        # handle triggers based on state
        if not event_lead_rule_skip:
            if vals.get('state') == 'open':
                self.env['event.lead.rule'].search([('lead_creation_trigger', '=', 'confirm')]).sudo()._run_on_registrations(self)
            elif vals.get('state') == 'done':
                self.env['event.lead.rule'].search([('lead_creation_trigger', '=', 'done')]).sudo()._run_on_registrations(self)

        return res

    def _load_records_create(self, values):
        """ In import mode: do not run rules those are intended to run when customers
        buy tickets, not when bootstrapping a database. """
        return super(EventRegistration, self.with_context(event_lead_rule_skip=True))._load_records_create(values)

    def _load_records_write(self, values):
        """ In import mode: do not run rules those are intended to run when customers
        buy tickets, not when bootstrapping a database. """
        return super(EventRegistration, self.with_context(event_lead_rule_skip=True))._load_records_write(values)

    def _update_leads(self, new_vals, lead_tracked_vals):
        """ Update leads linked to some registrations. Update is based depending
        on updated fields, see ``_get_lead_contact_fields()`` and ``_get_lead_
        description_fields()``. Main heuristic is

          * check attendee-based leads, for each registration recompute contact
            information if necessary (changing partner triggers the whole contact
            computation); update description if necessary;
          * check order-based leads, for each existing group-based lead, only
            partner change triggers a contact and description update. We consider
            that group-based rule works mainly with the main contact and less
            with further details of registrations. Those can be found in stat
            button if necessary.

        :param new_vals: values given to write. Used to determine updated fields;
        :param lead_tracked_vals: dict(registration_id, registration previous values)
          based on new_vals;
        """
        for registration in self:
            leads_attendee = registration.lead_ids.filtered(
                lambda lead: lead.event_lead_rule_id.lead_creation_basis == 'attendee'
            )
            if not leads_attendee:
                continue

            old_vals = lead_tracked_vals[registration.id]
            # if partner has been updated -> update registration contact information
            # as they are computed (and therefore not given to write values)
            if 'partner_id' in new_vals:
                new_vals.update(**dict(
                    (field, registration[field])
                    for field in self._get_lead_contact_fields()
                    if field != 'partner_id')
                )

            lead_values = {}
            # update contact fields: valid for all leads of registration
            upd_contact_fields = [field for field in self._get_lead_contact_fields() if field in new_vals.keys()]
            if any(new_vals[field] != old_vals[field] for field in upd_contact_fields):
                lead_values = registration._get_lead_contact_values()

            # update description fields: each lead has to be updated, otherwise
            # update in batch
            upd_description_fields = [field for field in self._get_lead_description_fields() if field in new_vals.keys()]
            if any(new_vals[field] != old_vals[field] for field in upd_description_fields):
                for lead in leads_attendee:
                    lead_values['description'] = "%s<br/>%s" % (
                        lead.description,
                        registration._get_lead_description(_("Updated registrations"), line_counter=True)
                    )
                    lead.write(lead_values)
            elif lead_values:
                leads_attendee.write(lead_values)

        leads_order = self.lead_ids.filtered(lambda lead: lead.event_lead_rule_id.lead_creation_basis == 'order')
        for lead in leads_order:
            lead_values = {}
            if new_vals.get('partner_id'):
                lead_values.update(lead.registration_ids._get_lead_contact_values())
                if not lead.partner_id:
                    lead_values['description'] = lead.registration_ids._get_lead_description(_("Participants"), line_counter=True)
                elif new_vals['partner_id'] != lead.partner_id.id:
                    lead_values['description'] = (lead.description or '') + "<br/>" + lead.registration_ids._get_lead_description(_("Updated registrations"), line_counter=True, line_suffix=_("(updated)"))
            if lead_values:
                lead.write(lead_values)

    def _get_lead_values(self, rule):
        """ Get lead values from registrations. Self can contain multiple records
        in which case first found non void value is taken. Note that all
        registrations should belong to the same event.

        :return dict lead_values: values used for create / write on a lead
        """
        lead_values = {
            # from rule
            'type': rule.lead_type,
            'user_id': rule.lead_user_id.id,
            'team_id': rule.lead_sales_team_id.id,
            'tag_ids': rule.lead_tag_ids.ids,
            'event_lead_rule_id': rule.id,
            # event and registration
            'event_id': self.event_id.id,
            'referred': self.event_id.name,
            'registration_ids': self.ids,
            'campaign_id': self._find_first_notnull('utm_campaign_id'),
            'source_id': self._find_first_notnull('utm_source_id'),
            'medium_id': self._find_first_notnull('utm_medium_id'),
        }
        lead_values.update(self._get_lead_contact_values())
        lead_values['description'] = self._get_lead_description(_("Participants"), line_counter=True)
        return lead_values

    def _get_lead_contact_values(self):
        """ Specific management of contact values. Rule creation basis has some
        effect on contact management

          * in attendee mode: keep registration partner only if partner phone and
            email match. Indeed lead are synchronized with their contact and it
            would imply rewriting on partner, and therefore on other documents;
          * in batch mode: if a customer is found use it as main contact. Registrations
            details are included in lead description;

        :return dict: values used for create / write on a lead
        """
        valid_partner = next(
            (reg.partner_id for reg in self if reg.partner_id != self.env.ref('base.public_partner')),
            self.env['res.partner']
        )  # CHECKME: broader than just public partner

        # mono registration mode: keep partner only if email and phone matches;
        # otherwise registration > partner. Note that email format and phone
        # formatting have to taken into account in comparison
        if len(self) == 1 and valid_partner:
            # compare emails: email_normalized or raw
            if self.email and valid_partner.email:
                if valid_partner.email_normalized and tools.email_normalize(self.email) != valid_partner.email_normalized:
                    valid_partner = self.env['res.partner']
                elif not valid_partner.email_normalized and valid_partner.email != self.email:
                    valid_partner = self.env['res.partner']

            # compare phone, taking into account formatting
            if valid_partner and self.phone and valid_partner.phone:
                phone_formatted = phone_validation.phone_format(
                    self.phone,
                    valid_partner.country_id.code or None,
                    valid_partner.country_id.phone_code or None,
                    force_format='E164',
                    raise_exception=False
                )
                partner_phone_formatted = valid_partner._phone_format(valid_partner.phone)
                if phone_formatted and partner_phone_formatted and phone_formatted != partner_phone_formatted:
                    valid_partner = self.env['res.partner']
                if (not phone_formatted or not partner_phone_formatted) and self.phone != valid_partner.phone:
                    valid_partner = self.env['res.partner']

        if valid_partner:
            contact_vals = self.env['crm.lead']._prepare_values_from_partner(valid_partner)
            # force email_from / phone only if not set on partner because those fields are now synchronized automatically
            if not valid_partner.email:
                contact_vals['email_from'] = self._find_first_notnull('email')
            if not valid_partner.phone:
                contact_vals['phone'] = self._find_first_notnull('phone')
        else:
            # don't force email_from + partner_id because those fields are now synchronized automatically
            contact_vals = {
                'contact_name': self._find_first_notnull('name'),
                'email_from': self._find_first_notnull('email'),
                'phone': self._find_first_notnull('phone'),
                'lang_id': False,
            }
        contact_name = valid_partner.name or self._find_first_notnull('name') or self._find_first_notnull('email')
        contact_vals.update({
            'name': f'{self.event_id[:1].name} - {contact_name}',
            'partner_id': valid_partner.id,
            'mobile': valid_partner.mobile or self._find_first_notnull('mobile'),
        })
        return contact_vals

    def _get_lead_description(self, prefix='', line_counter=True, line_suffix=''):
        """ Build the description for the lead using a prefix for all generated
        lines. For example to enumerate participants or inform of an update in
        the information of a participant.

        :return string description: complete description for a lead taking into
          account all registrations contained in self
        """
        reg_lines = [
            registration._get_lead_description_registration(
                line_suffix=line_suffix
            ) for registration in self
        ]
        description = (prefix if prefix else '') + Markup("<br/>")
        if line_counter:
            description += Markup("<ol>") + Markup('').join(reg_lines) + Markup("</ol>")
        else:
            description += Markup("<ul>") + Markup('').join(reg_lines) + Markup("</ul>")
        return description

    def _get_lead_description_registration(self, line_suffix=''):
        """ Build the description line specific to a given registration. """
        self.ensure_one()
        return Markup("<li>") + "%s (%s)%s" % (
            self.name or self.partner_id.name or self.email,
            " - ".join(self[field] for field in ('email', 'phone') if self[field]),
            f" {line_suffix}" if line_suffix else "",
        ) + Markup("</li>")

    def _get_lead_tracked_values(self):
        """ Tracked values are based on two subset of fields to track in order
        to fill or update leads. Two main use cases are

          * description fields: registration contact fields: email, phone, ...
            on registration. Other fields are added by inheritance like
            question answers;
          * contact fields: registration contact fields + partner_id field as
            contact of a lead is managed specifically. Indeed email and phone
            synchronization of lead / partner_id implies paying attention to
            not rewrite partner values from registration values.

        Tracked values are therefore the union of those two field sets. """
        tracked_fields = list(set(self._get_lead_contact_fields()) | set(self._get_lead_description_fields()))
        return dict(
            (registration.id,
             dict((field, self._convert_value(registration[field], field)) for field in tracked_fields)
            ) for registration in self
        )

    def _get_lead_grouping(self, rules, rule_to_new_regs):
        """ Perform grouping of registrations in order to enable order-based
        lead creation and update existing groups with new registrations.

        Heuristic in event is the following. Registrations created in multi-mode
        are grouped by event. Customer use case: website_event flow creates
        several registrations in a create-multi.

        Update is not supported as there is no way to determine if a registration
        is part of an existing batch.

        :param rules: lead creation rules to run on registrations given by self;
        :param rule_to_new_regs: dict: for each rule, subset of self matching
          rule conditions. Used to speedup batch computation;

        :return dict: for each rule, rule (key of dict) gives a list of groups.
          Each group is a tuple (
            existing_lead: existing lead to update;
            group_record: record used to group;
            registrations: sub record set of self, containing registrations
                           belonging to the same group;
          )
        """
        event_to_reg_ids = defaultdict(lambda: self.env['event.registration'])
        for registration in self:
            event_to_reg_ids[registration.event_id] += registration

        return dict(
            (rule, [(False, event, (registrations & rule_to_new_regs[rule]).sorted('id'))
                    for event, registrations in event_to_reg_ids.items()])
            for rule in rules
        )

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    @api.model
    def _get_lead_contact_fields(self):
        """ Get registration fields linked to lead contact. Those are used notably
        to see if an update of lead is necessary or to fill contact values
        in ``_get_lead_contact_values())`` """
        return ['name', 'email', 'phone', 'mobile', 'partner_id']

    @api.model
    def _get_lead_description_fields(self):
        """ Get registration fields linked to lead description. Those are used
        notablyto see if an update of lead is necessary or to fill description
        in ``_get_lead_description())`` """
        return ['name', 'email', 'phone']

    def _find_first_notnull(self, field_name):
        """ Small tool to extract the first not nullvalue of a field: its value
        or the ids if this is a relational field. """
        value = next((reg[field_name] for reg in self if reg[field_name]), False)
        return self._convert_value(value, field_name)

    def _convert_value(self, value, field_name):
        """ Small tool because convert_to_write is touchy """
        if isinstance(value, models.BaseModel) and self._fields[field_name].type in ['many2many', 'one2many']:
            return value.ids
        if isinstance(value, models.BaseModel) and self._fields[field_name].type == 'many2one':
            return value.id
        return value
