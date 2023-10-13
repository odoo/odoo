# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
from collections import defaultdict

from odoo import fields, models, _


class EventLeadRule(models.Model):
    """ Rule model for creating / updating leads from event registrations.

    SPECIFICATIONS: CREATION TYPE

    There are two types of lead creation:

      * per attendee: create a lead for each registration;
      * per order: create a lead for a group of registrations;

    The last one is only available through interface if it is possible to register
    a group of attendees in one action (when event_sale or website_event are
    installed). Behavior itself is implemented directly in event_crm.

    Basically a group is either a list of registrations belonging to the same
    event and created in batch (website_event flow). With event_sale this
    definition will be improved to be based on sale_order.

    SPECIFICATIONS: CREATION TRIGGERS

    There are three options to trigger lead creation. We consider basically that
    lead quality increases if attendees confirmed or went to the event. Triggers
    allow therefore to run rules:

      * at attendee creation;
      * at attendee confirmation;
      * at attendee venue;

    This trigger defines when the rule will run.

    SPECIFICATIONS: FILTERING REGISTRATIONS

    When a batch of registrations matches the rule trigger we filter them based
    on conditions and rules defines on event_lead_rule model. Heuristic is the
    following:

      * the rule is active;
      * if a filter is set: filter registrations based on this filter. This is
        done like a search, and filter is a domain;
      * if a company is set on the rule, it must match event's company. Note
        that multi-company rules apply on event_lead_rule;
      * if an event category it set, it must match;
      * if an event is set, it must match;
      * if both event and category are set, one of them must match (OR). If none
        of those are set, it is considered as OK;

    If conditions are met, leads are created with pre-filled informations defined
    on the rule (type, user_id, team_id). Contact information coming from the
    registrations are computed (customer, name, email, phone, contact_name).

    SPECIFICATIONS: OTHER POINTS

    Note that all rules matching their conditions are applied. This means more
    than one lead can be created depending on the configuration. This is
    intended in order to give more freedom to the user using the automatic
    lead generation.
    """
    _name = "event.lead.rule"
    _description = "Event Lead Rules"

    # Definition
    name = fields.Char('Rule Name', required=True, translate=True)
    active = fields.Boolean('Active', default=True)
    lead_ids = fields.One2many(
        'crm.lead', 'event_lead_rule_id', string='Created Leads',
        groups='sales_team.group_sale_salesman')
    # Triggers
    lead_creation_basis = fields.Selection([
        ('attendee', 'Per Attendee'), ('order', 'Per Order')],
        string='Create', default='attendee', required=True,
        help='Per Attendee: A Lead is created for each Attendee (B2C).\n'
             'Per Order: A single Lead is created per Ticket Batch/Sale Order (B2B)')
    lead_creation_trigger = fields.Selection([
        ('create', 'Attendees are created'),
        ('confirm', 'Attendees are registered'),
        ('done', 'Attendees attended')],
        string='When', default='create', required=True,
        help='Creation: at attendee creation;\n'
             'Registered: at attendee registration, manually or automatically;\n'
             'Attended: when attendance is confirmed and registration set to done;')
    # Filters
    event_type_ids = fields.Many2many(
        'event.type', string='Event Categories',
        help='Filter the attendees to include those of this specific event category. If not set, no event category restriction will be applied.')
    event_id = fields.Many2one(
        'event.event', string='Event',
        check_company=True,
        help='Filter the attendees to include those of this specific event. If not set, no event restriction will be applied.')
    company_id = fields.Many2one(
        'res.company', string='Company',
        help="Restrict the trigger of this rule to events belonging to a specific company.\nIf not set, no company restriction will be applied.")
    event_registration_filter = fields.Text(string="Registrations Domain", help="Filter the attendees that will or not generate leads.")
    # Lead default_value fields
    lead_type = fields.Selection([
        ('lead', 'Lead'), ('opportunity', 'Opportunity')], string="Lead Type", required=True,
        default=lambda self: 'lead' if self.env['res.users'].has_group('crm.group_use_lead') else 'opportunity',
        help="Default lead type when this rule is applied.")
    lead_sales_team_id = fields.Many2one(
        'crm.team', string='Sales Team', ondelete="set null",
        help="Automatically assign the created leads to this Sales Team.")
    lead_user_id = fields.Many2one('res.users', string='Salesperson', help="Automatically assign the created leads to this Salesperson.")
    lead_tag_ids = fields.Many2many('crm.tag', string='Tags', help="Automatically add these tags to the created leads.")

    def _run_on_registrations(self, registrations):
        """ Create or update leads based on rule configuration. Two main lead
        management type exists

          * per attendee: each registration creates a lead;
          * per order: registrations are grouped per group and one lead is created
            or updated with the batch (used mainly with sale order configuration
            in event_sale);

        Heuristic

          * first, check existing lead linked to registrations to ensure no
            duplication. Indeed for example attendee status change may trigger
            the same rule several times;
          * then for each rule, get the subset of registrations matching its
            filters;
          * then for each order-based rule, get the grouping information. This
            give a list of registrations by group (event, sale_order), with maybe
            an already-existing lead to update instead of creating a new one;
          * finally apply rules. Attendee-based rules create a lead for each
            attendee, group-based rules use the grouping information to create
            or update leads;

        :param registrations: event.registration recordset on which rules given by
          self have to run. Triggers should already be checked, only filters are
          applied here.

        :return leads: newly-created leads. Updated leads are not returned.
        """
        # order by ID, ensure first created wins
        registrations = registrations.sorted('id')

        # first: ensure no duplicate by searching existing registrations / rule
        existing_leads = self.env['crm.lead'].search([
            ('registration_ids', 'in', registrations.ids),
            ('event_lead_rule_id', 'in', self.ids)
        ])
        rule_to_existing_regs = defaultdict(lambda: self.env['event.registration'])
        for lead in existing_leads:
            rule_to_existing_regs[lead.event_lead_rule_id] += lead.registration_ids

        # second: check registrations matching rules (in batch)
        new_registrations = self.env['event.registration']
        rule_to_new_regs = dict()
        for rule in self:
            new_for_rule = registrations.filtered(lambda reg: reg not in rule_to_existing_regs[rule])
            rule_registrations = rule._filter_registrations(new_for_rule)
            new_registrations |= rule_registrations
            rule_to_new_regs[rule] = rule_registrations
        new_registrations.sorted('id')  # as an OR was used, re-ensure order

        # third: check grouping
        order_based_rules = self.filtered(lambda rule: rule.lead_creation_basis == 'order')
        rule_group_info = new_registrations._get_lead_grouping(order_based_rules, rule_to_new_regs)

        lead_vals_list = []
        for rule in self:
            if rule.lead_creation_basis == 'attendee':
                matching_registrations = rule_to_new_regs[rule].sorted('id')
                for registration in matching_registrations:
                    lead_vals_list.append(registration._get_lead_values(rule))
            else:
                # check if registrations are part of a group, for example a sale order, to know if we update or create leads
                for (toupdate_leads, group_key, group_registrations) in rule_group_info[rule]:
                    if toupdate_leads:
                        additionnal_description = group_registrations._get_lead_description(_("New registrations"), line_counter=True)
                        for lead in toupdate_leads:
                            lead.write({
                                'description': "%s<br/>%s" % (lead.description, additionnal_description),
                                'registration_ids': [(4, reg.id) for reg in group_registrations],
                            })
                    elif group_registrations:
                        lead_vals_list.append(group_registrations._get_lead_values(rule))

        return self.env['crm.lead'].create(lead_vals_list)

    def _filter_registrations(self, registrations):
        """ Keep registrations matching rule conditions. Those are

          * if a filter is set: filter registrations based on this filter. This is
            done like a search, and filter is a domain;
          * if a company is set on the rule, it must match event's company. Note
            that multi-company rules apply on event_lead_rule;
          * if an event category it set, it must match;
          * if an event is set, it must match;
          * if both event and category are set, one of them must match (OR). If none
            of those are set, it is considered as OK;

        :param registrations: event.registration recordset on which rule filters
          will be evaluated;
        :return: subset of registrations matching rules
        """
        self.ensure_one()
        if self.event_registration_filter and self.event_registration_filter != '[]':
            registrations = registrations.filtered_domain(literal_eval(self.event_registration_filter))

        # check from direct m2o to linked m2o / o2m to filter first without inner search
        company_ok = lambda registration: registration.company_id == self.company_id if self.company_id else True
        event_or_event_type_ok = \
            lambda registration: \
                registration.event_id == self.event_id or registration.event_id.event_type_id in self.event_type_ids \
                if (self.event_id or self.event_type_ids) else True

        return registrations.filtered(lambda r: company_ok(r) and event_or_event_type_ok(r))
