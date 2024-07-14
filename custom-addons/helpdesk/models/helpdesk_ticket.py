# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
from dateutil.relativedelta import relativedelta

from odoo import api, Command, fields, models, tools, _
from odoo.exceptions import AccessError
from odoo.osv import expression
from odoo.addons.web.controllers.utils import clean_action

TICKET_PRIORITY = [
    ('0', 'Low priority'),
    ('1', 'Medium priority'),
    ('2', 'High priority'),
    ('3', 'Urgent'),
]

class HelpdeskTicket(models.Model):
    _name = 'helpdesk.ticket'
    _description = 'Helpdesk Ticket'
    _order = 'priority desc, id desc'
    _primary_email = 'partner_email'
    _inherit = [
        'portal.mixin',
        'mail.thread.cc',
        'utm.mixin',
        'rating.mixin',
        'mail.activity.mixin',
        'mail.tracking.duration.mixin',
    ]
    _track_duration_field = 'stage_id'

    @api.model
    def default_get(self, fields):
        result = super(HelpdeskTicket, self).default_get(fields)
        if result.get('team_id') and fields:
            team = self.env['helpdesk.team'].browse(result['team_id'])
            if 'user_id' in fields and 'user_id' not in result:  # if no user given, deduce it from the team
                result['user_id'] = team._determine_user_to_assign()[team.id].id
            if 'stage_id' in fields and 'stage_id' not in result:  # if no stage given, deduce it from the team
                result['stage_id'] = team._determine_stage()[team.id].id
        return result

    def _default_team_id(self):
        team_id = self.env['helpdesk.team'].search([('member_ids', 'in', self.env.uid)], limit=1).id
        if not team_id:
            team_id = self.env['helpdesk.team'].search([], limit=1).id
        return team_id

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        # write the domain
        # - ('id', 'in', stages.ids): add columns that should be present
        # - OR ('team_ids', '=', team_id) if team_id: add team columns
        search_domain = [('id', 'in', stages.ids)]
        if self.env.context.get('default_team_id'):
            search_domain = ['|', ('team_ids', 'in', self.env.context['default_team_id'])] + search_domain

        return stages.search(search_domain, order=order)

    name = fields.Char(string='Subject', required=True, index=True, tracking=True)
    team_id = fields.Many2one('helpdesk.team', string='Helpdesk Team', default=_default_team_id, index=True, tracking=True)
    use_sla = fields.Boolean(related='team_id.use_sla')
    team_privacy_visibility = fields.Selection(related='team_id.privacy_visibility', string="Team Visibility")
    description = fields.Html(sanitize_attributes=False)
    active = fields.Boolean(default=True)
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', string="Type", tracking=True)
    tag_ids = fields.Many2many('helpdesk.tag', string='Tags')
    company_id = fields.Many2one(related='team_id.company_id', string='Company', store=True, readonly=True)
    color = fields.Integer(string='Color Index')
    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')], string='Kanban State',
        copy=False, default='normal', required=True)
    kanban_state_label = fields.Char(compute='_compute_kanban_state_label', string='Kanban State Label', tracking=True)
    legend_blocked = fields.Char(related='stage_id.legend_blocked', string='Kanban Blocked Explanation', readonly=True, related_sudo=False)
    legend_done = fields.Char(related='stage_id.legend_done', string='Kanban Valid Explanation', readonly=True, related_sudo=False)
    legend_normal = fields.Char(related='stage_id.legend_normal', string='Kanban Ongoing Explanation', readonly=True, related_sudo=False)
    domain_user_ids = fields.Many2many('res.users', compute='_compute_domain_user_ids')
    user_id = fields.Many2one(
        'res.users', string='Assigned to', compute='_compute_user_and_stage_ids', store=True,
        readonly=False, tracking=True,
        domain=lambda self: [('groups_id', 'in', self.env.ref('helpdesk.group_helpdesk_user').id)])
    properties = fields.Properties(
        'Properties', definition='team_id.ticket_properties',
        copy=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True, index=True)
    partner_ticket_ids = fields.Many2many('helpdesk.ticket', compute='_compute_partner_ticket_count', string="Partner Tickets")
    partner_ticket_count = fields.Integer('Number of other tickets from the same partner', compute='_compute_partner_ticket_count')
    partner_open_ticket_count = fields.Integer('Number of other open tickets from the same partner', compute='_compute_partner_ticket_count')
    # Used to submit tickets from a contact form
    partner_name = fields.Char(string='Customer Name', compute='_compute_partner_name', store=True, readonly=False)
    partner_email = fields.Char(string='Customer Email', compute='_compute_partner_email', inverse="_inverse_partner_email", store=True, readonly=False)
    partner_phone = fields.Char(string='Customer Phone', compute='_compute_partner_phone', inverse="_inverse_partner_phone", store=True, readonly=False)
    commercial_partner_id = fields.Many2one(related="partner_id.commercial_partner_id")
    closed_by_partner = fields.Boolean('Closed by Partner', readonly=True)
    priority = fields.Selection(TICKET_PRIORITY, string='Priority', default='0', tracking=True)
    stage_id = fields.Many2one(
        'helpdesk.stage', string='Stage', compute='_compute_user_and_stage_ids', store=True,
        readonly=False, ondelete='restrict', tracking=1, group_expand='_read_group_stage_ids',
        copy=False, index=True, domain="[('team_ids', '=', team_id)]")
    fold = fields.Boolean(related="stage_id.fold")
    date_last_stage_update = fields.Datetime("Last Stage Update", copy=False, readonly=True)
    ticket_ref = fields.Char(string='Ticket IDs Sequence', copy=False, readonly=True, index=True)
    # next 4 fields are computed in write (or create)
    assign_date = fields.Datetime("First assignment date")
    assign_hours = fields.Integer("Time to first assignment (hours)", compute='_compute_assign_hours', store=True)
    close_date = fields.Datetime("Close date", copy=False)
    close_hours = fields.Integer("Time to close (hours)", compute='_compute_close_hours', store=True)
    open_hours = fields.Integer("Open Time (hours)", compute='_compute_open_hours', search='_search_open_hours')
    # SLA relative
    sla_ids = fields.Many2many('helpdesk.sla', 'helpdesk_sla_status', 'ticket_id', 'sla_id', string="SLAs", copy=False)
    sla_status_ids = fields.One2many('helpdesk.sla.status', 'ticket_id', string="SLA Status")
    sla_reached_late = fields.Boolean("Has SLA reached late", compute='_compute_sla_reached_late', compute_sudo=True, store=True)
    sla_reached = fields.Boolean("Has SLA reached", compute='_compute_sla_reached', compute_sudo=True, store=True)
    sla_deadline = fields.Datetime("SLA Deadline", compute='_compute_sla_deadline', compute_sudo=True, store=True)
    sla_deadline_hours = fields.Float("Hours to SLA Deadline", compute='_compute_sla_deadline', compute_sudo=True, store=True)
    sla_fail = fields.Boolean("Failed SLA Policy", compute='_compute_sla_fail', search='_search_sla_fail')
    sla_success = fields.Boolean("Success SLA Policy", compute='_compute_sla_success', search='_search_sla_success')

    use_credit_notes = fields.Boolean(related='team_id.use_credit_notes', string='Use Credit Notes')
    use_coupons = fields.Boolean(related='team_id.use_coupons', string='Use Coupons')
    use_product_returns = fields.Boolean(related='team_id.use_product_returns', string='Use Returns')
    use_product_repairs = fields.Boolean(related='team_id.use_product_repairs', string='Use Repairs')
    use_rating = fields.Boolean(related='team_id.use_rating', string='Use Customer Ratings')

    is_partner_email_update = fields.Boolean('Partner Email will Update', compute='_compute_is_partner_email_update')
    is_partner_phone_update = fields.Boolean('Partner Phone will Update', compute='_compute_is_partner_phone_update')
    # customer portal: include comment and (incoming/outgoing) emails in communication history
    website_message_ids = fields.One2many(domain=lambda self: [('model', '=', self._name), ('message_type', 'in', ['email', 'comment', 'email_outgoing'])])

    first_response_hours = fields.Float("Hours to First Response")
    avg_response_hours = fields.Float("Average Hours to Respond")
    oldest_unanswered_customer_message_date = fields.Datetime("Oldest Unanswered Customer Message Date")
    answered_customer_message_count = fields.Integer('# Exchanges')
    total_response_hours = fields.Float("Total Exchange Time in Hours")
    display_extra_info = fields.Boolean(compute="_compute_display_extra_info")

    @api.depends('stage_id', 'kanban_state')
    def _compute_kanban_state_label(self):
        for ticket in self:
            if ticket.kanban_state == 'normal':
                ticket.kanban_state_label = ticket.legend_normal
            elif ticket.kanban_state == 'blocked':
                ticket.kanban_state_label = ticket.legend_blocked
            else:
                ticket.kanban_state_label = ticket.legend_done

    @api.depends('team_id')
    def _compute_domain_user_ids(self):
        user_ids = self.env.ref('helpdesk.group_helpdesk_user').users.ids
        for ticket in self:
            ticket_user_ids = []
            ticket_sudo = ticket.sudo()
            if ticket_sudo.team_id and ticket_sudo.team_id.privacy_visibility == 'invited_internal':
                ticket_user_ids = ticket_sudo.team_id.message_partner_ids.user_ids.ids
            ticket.domain_user_ids = [Command.set(user_ids + ticket_user_ids)]

    def _compute_access_url(self):
        super(HelpdeskTicket, self)._compute_access_url()
        for ticket in self:
            ticket.access_url = '/my/ticket/%s' % ticket.id

    @api.depends('sla_status_ids.deadline', 'sla_status_ids.reached_datetime')
    def _compute_sla_reached_late(self):
        """ Required to do it in SQL since we need to compare 2 columns value """
        mapping = {}
        if self.ids:
            self.env.cr.execute("""
                SELECT ticket_id, COUNT(id) AS reached_late_count
                FROM helpdesk_sla_status
                WHERE ticket_id IN %s AND (deadline < reached_datetime OR (deadline < %s AND reached_datetime IS NULL))
                GROUP BY ticket_id
            """, (tuple(self.ids), fields.Datetime.now()))
            mapping = dict(self.env.cr.fetchall())

        for ticket in self:
            ticket.sla_reached_late = mapping.get(ticket.id, 0) > 0

    @api.depends('sla_status_ids.deadline', 'sla_status_ids.reached_datetime')
    def _compute_sla_reached(self):
        sla_status_read_group = self.env['helpdesk.sla.status']._read_group(
            [('exceeded_hours', '<', 0), ('ticket_id', 'in', self.ids)],
            ['ticket_id'],
        )
        sla_status_ids_per_ticket = {ticket.id for [ticket] in sla_status_read_group}
        for ticket in self:
            ticket.sla_reached = ticket.id in sla_status_ids_per_ticket

    @api.depends('sla_status_ids.deadline', 'sla_status_ids.reached_datetime')
    def _compute_sla_deadline(self):
        """ Keep the deadline for the last stage (closed one), so a closed ticket can have a status failed.
            Note: a ticket in a closed stage will probably have no deadline
        """
        now = fields.Datetime.now()
        for ticket in self:

            # the current team is invalid, no need to compute new values since the transaction will be rolled back anyway.
            if not ticket.team_id:
                continue
            min_deadline = False
            for status in ticket.sla_status_ids:
                if status.reached_datetime or not status.deadline:
                    continue
                if not min_deadline or status.deadline < min_deadline:
                    min_deadline = status.deadline

            ticket.update({
                'sla_deadline': min_deadline,
                'sla_deadline_hours': ticket.team_id.resource_calendar_id.get_work_duration_data\
                    (now, min_deadline, compute_leaves=True)['hours'] if min_deadline else 0.0,
            })

    @api.depends('sla_deadline', 'sla_reached_late')
    def _compute_sla_fail(self):
        now = fields.Datetime.now()
        for ticket in self:
            if ticket.sla_deadline:
                ticket.sla_fail = (ticket.sla_deadline < now) or ticket.sla_reached_late
            else:
                ticket.sla_fail = ticket.sla_reached_late

    @api.depends('partner_email', 'partner_id')
    def _compute_is_partner_email_update(self):
        for ticket in self:
            ticket.is_partner_email_update = ticket._get_partner_email_update()

    @api.depends('partner_phone', 'partner_id')
    def _compute_is_partner_phone_update(self):
        for ticket in self:
            ticket.is_partner_phone_update = ticket._get_partner_phone_update()

    @api.model
    def _search_sla_fail(self, operator, value):
        datetime_now = fields.Datetime.now()
        if (value and operator in expression.NEGATIVE_TERM_OPERATORS) or (not value and operator not in expression.NEGATIVE_TERM_OPERATORS):  # is not failed
            return ['&', ('sla_reached_late', '=', False), '|', ('sla_deadline', '=', False), ('sla_deadline', '>=', datetime_now)]
        return ['|', ('sla_reached_late', '=', True), ('sla_deadline', '<', datetime_now)]  # is failed

    @api.depends('sla_deadline', 'sla_reached_late')
    def _compute_sla_success(self):
        now = fields.Datetime.now()
        for ticket in self:
            ticket.sla_success = (ticket.sla_deadline and ticket.sla_deadline > now)

    @api.model
    def _search_sla_success(self, operator, value):
        datetime_now = fields.Datetime.now()
        if (value and operator in expression.NEGATIVE_TERM_OPERATORS) or (not value and operator not in expression.NEGATIVE_TERM_OPERATORS):  # is failed
            return [('sla_status_ids.reached_datetime', '>', datetime_now), ('sla_reached_late', '!=', False), '|', ('sla_deadline', '!=', False), ('sla_deadline', '<', datetime_now)]
        return [('sla_status_ids.reached_datetime', '<', datetime_now), ('sla_reached', '=', True), ('sla_reached_late', '=', False), '|', ('sla_deadline', '=', False), ('sla_deadline', '>=', datetime_now)]  # is success

    @api.depends('team_id')
    def _compute_user_and_stage_ids(self):
        for ticket in self.filtered(lambda ticket: ticket.team_id):
            if not ticket.user_id:
                ticket.user_id = ticket.team_id._determine_user_to_assign()[ticket.team_id.id]
            if not ticket.stage_id or ticket.stage_id not in ticket.team_id.stage_ids:
                ticket.stage_id = ticket.team_id._determine_stage()[ticket.team_id.id]

    @api.depends('partner_id')
    def _compute_partner_name(self):
        for ticket in self:
            if ticket.partner_id:
                ticket.partner_name = ticket.partner_id.name

    @api.depends('partner_id.email')
    def _compute_partner_email(self):
        for ticket in self:
            if ticket.partner_id:
                ticket.partner_email = ticket.partner_id.email

    def _inverse_partner_email(self):
        for ticket in self:
            if ticket._get_partner_email_update():
                ticket.partner_id.email = ticket.partner_email

    @api.depends('partner_id.phone')
    def _compute_partner_phone(self):
        for ticket in self:
            if ticket.partner_id:
                ticket.partner_phone = ticket.partner_id.phone

    def _inverse_partner_phone(self):
        for ticket in self:
            if (ticket._get_partner_phone_update() or not ticket.partner_id.phone) and ticket.partner_phone:
                ticket = ticket.sudo()
                ticket.partner_id.phone = ticket.partner_phone

    @api.depends('partner_id', 'partner_email', 'partner_phone')
    def _compute_partner_ticket_count(self):
        for ticket in self:
            partner_tickets = self.search([("partner_id", "child_of", ticket.partner_id.commercial_partner_id.id)]) if ticket.partner_id else ticket
            ticket.partner_ticket_ids = partner_tickets
            partner_tickets = partner_tickets - ticket._origin
            ticket.partner_ticket_count = len(partner_tickets) if partner_tickets else 0
            partner_tickets.fetch(['stage_id'])  # prevent over-fetching fields, leading to potential out-of-memory error
            open_ticket = partner_tickets.filtered(lambda ticket: not ticket.stage_id.fold)
            ticket.partner_open_ticket_count = len(open_ticket)

    @api.depends('assign_date')
    def _compute_assign_hours(self):
        for ticket in self:
            create_date = fields.Datetime.from_string(ticket.create_date)
            if create_date and ticket.assign_date and ticket.team_id.resource_calendar_id:
                duration_data = ticket.team_id.resource_calendar_id.get_work_duration_data(create_date, fields.Datetime.from_string(ticket.assign_date), compute_leaves=True)
                ticket.assign_hours = duration_data['hours']
            else:
                ticket.assign_hours = False

    @api.depends('create_date', 'close_date')
    def _compute_close_hours(self):
        for ticket in self:
            create_date = fields.Datetime.from_string(ticket.create_date)
            if create_date and ticket.close_date and ticket.team_id:
                duration_data = ticket.team_id.resource_calendar_id.get_work_duration_data(create_date, fields.Datetime.from_string(ticket.close_date), compute_leaves=True)
                ticket.close_hours = duration_data['hours']
            else:
                ticket.close_hours = False

    @api.depends('close_hours')
    def _compute_open_hours(self):
        for ticket in self:
            if ticket.create_date:  # fix from https://github.com/odoo/enterprise/commit/928fbd1a16e9837190e9c172fa50828fae2a44f7
                if ticket.close_date:
                    time_difference = ticket.close_date - fields.Datetime.from_string(ticket.create_date)
                else:
                    time_difference = fields.Datetime.now() - fields.Datetime.from_string(ticket.create_date)
                ticket.open_hours = (time_difference.seconds) / 3600 + time_difference.days * 24
            else:
                ticket.open_hours = 0

    def _compute_display_extra_info(self):
        self.display_extra_info = self.env.user.has_group('base.group_multi_company')

    @api.model
    def _search_open_hours(self, operator, value):
        dt = fields.Datetime.now() - relativedelta(hours=value)

        d1, d2 = False, False
        if operator in ['<', '<=', '>', '>=']:
            d1 = ['&', ('close_date', '=', False), ('create_date', expression.TERM_OPERATORS_NEGATION[operator], dt)]
            d2 = ['&', ('close_date', '!=', False), ('close_hours', operator, value)]
        elif operator in ['=', '!=']:
            subdomain = ['&', ('create_date', '>=', dt.replace(minute=0, second=0, microsecond=0)), ('create_date', '<=', dt.replace(minute=59, second=59, microsecond=99))]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                subdomain = expression.distribute_not(subdomain)
            d1 = expression.AND([[('close_date', '=', False)], subdomain])
            d2 = ['&', ('close_date', '!=', False), ('close_hours', operator, value)]
        return expression.OR([d1, d2])

    def _get_partner_email_update(self):
        self.ensure_one()
        if self.partner_id.email and self.partner_email != self.partner_id.email:
            ticket_email_normalized = tools.email_normalize(self.partner_email) or self.partner_email or False
            partner_email_normalized = tools.email_normalize(self.partner_id.email) or self.partner_id.email or False
            return ticket_email_normalized != partner_email_normalized
        return False

    def _get_partner_phone_update(self):
        self.ensure_one()
        if self.partner_id.phone and self.partner_phone != self.partner_id.phone:
            ticket_phone_formatted = self.partner_phone or False
            partner_phone_formatted = self.partner_id.phone or False
            return ticket_phone_formatted != partner_phone_formatted
        return False

    def action_customer_preview(self):
        self.ensure_one()
        if self.team_privacy_visibility != 'portal' or not self.partner_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'message': _('At this time, there is no customer preview available to show. The current ticket cannot be accessed by the customer, as it belongs to a helpdesk team that is not publicly available, or there is no customer associated with the ticket.'),
                }
            }
        return {
            'type': 'ir.actions.act_url',
            'url': self.get_portal_url(),
            'target': 'self',
        }

    # ------------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------------

    @api.depends('ticket_ref', 'partner_name')
    @api.depends_context('with_partner')
    def _compute_display_name(self):
        display_partner_name = self._context.get('with_partner', False)
        ticket_with_name = self.filtered('name')
        for ticket in ticket_with_name:
            name = f'{ticket.name} (#{ticket.ticket_ref})'
            if display_partner_name and ticket.partner_name:
                name += f' - {ticket.partner_name}'
            ticket.display_name = name
        return super(HelpdeskTicket, self - ticket_with_name)._compute_display_name()

    @api.model
    def get_empty_list_help(self, help_message):
        self = self.with_context(
            empty_list_help_id=self.env.context.get('default_team_id'),
            empty_list_help_model='helpdesk.team',
            empty_list_help_document_name=_("tickets"),
        )
        return super(HelpdeskTicket, self).get_empty_list_help(help_message)

    def create_action(self, action_ref, title, search_view_ref):
        action = self.env["ir.actions.actions"]._for_xml_id(action_ref)
        action = clean_action(action, self.env)
        if title:
            action['display_name'] = title
        if search_view_ref:
            action['search_view_id'] = self.env.ref(search_view_ref).read()[0]
        if 'views' not in action:
            action['views'] = [(False, view) for view in action['view_mode'].split(",")]
        return action

    @api.model
    def _find_or_create_partner(self, partner_name, partner_email, company=False):
        parsed_name, parsed_email_normalized = tools.parse_contact_from_email(partner_email)
        if not parsed_name:
            parsed_name = partner_name
        return self.env['res.partner'].with_context(default_company_id=company).find_or_create(
            tools.formataddr((parsed_name, parsed_email_normalized))
        )

    @api.model_create_multi
    def create(self, list_value):
        now = fields.Datetime.now()
        # determine user_id and stage_id if not given. Done in batch.
        teams = self.env['helpdesk.team'].browse([vals['team_id'] for vals in list_value if vals.get('team_id')])
        team_default_map = dict.fromkeys(teams.ids, dict())
        for team in teams:
            team_default_map[team.id] = {
                'stage_id': team._determine_stage()[team.id].id,
                'user_id': team._determine_user_to_assign()[team.id].id
            }

        # Manually create a partner now since '_generate_template_recipients' doesn't keep the name. This is
        # to avoid intrusive changes in the 'mail' module
        # TDE TODO: to extract and clean in mail thread
        for vals in list_value:
            partner_id = vals.get('partner_id', False)
            partner_name = vals.get('partner_name', False)
            partner_email = vals.get('partner_email', False)
            if partner_name and partner_email and not partner_id:
                company = False
                if vals.get('team_id'):
                    team = self.env['helpdesk.team'].browse(vals.get('team_id'))
                    company = team.company_id.id
                vals['partner_id'] = self._find_or_create_partner(partner_name, partner_email, company).id

        # determine partner email for ticket with partner but no email given
        partners = self.env['res.partner'].browse([vals['partner_id'] for vals in list_value if 'partner_id' in vals and vals.get('partner_id') and 'partner_email' not in vals])
        partner_email_map = {partner.id: partner.email for partner in partners}
        partner_name_map = {partner.id: partner.name for partner in partners}
        company_per_team_id = {t.id: t.company_id for t in teams}
        for vals in list_value:
            company = company_per_team_id.get(vals.get('team_id', False))
            vals['ticket_ref'] = self.env['ir.sequence'].with_company(company).sudo().next_by_code('helpdesk.ticket')
            if vals.get('team_id'):
                team_default = team_default_map[vals['team_id']]
                if 'stage_id' not in vals:
                    vals['stage_id'] = team_default['stage_id']
                # Note: this will break the randomly distributed user assignment. Indeed, it will be too difficult to
                # equally assigned user when creating ticket in batch, as it requires to search after the last assigned
                # after every ticket creation, which is not very performant. We decided to not cover this user case.
                if 'user_id' not in vals:
                    vals['user_id'] = team_default['user_id']
                if vals.get('user_id'):  # if a user is finally assigned, force ticket assign_date and reset assign_hours
                    vals['assign_date'] = fields.Datetime.now()
                    vals['assign_hours'] = 0

            # set partner email if in map of not given
            if vals.get('partner_id') in partner_email_map:
                vals['partner_email'] = partner_email_map.get(vals['partner_id'])
            # set partner name if in map of not given
            if vals.get('partner_id') in partner_name_map:
                vals['partner_name'] = partner_name_map.get(vals['partner_id'])

            if vals.get('stage_id'):
                vals['date_last_stage_update'] = now
            vals['oldest_unanswered_customer_message_date'] = now

        # context: no_log, because subtype already handle this
        tickets = super(HelpdeskTicket, self).create(list_value)

        # make customer follower
        for ticket in tickets:
            if ticket.partner_id:
                ticket.message_subscribe(partner_ids=ticket.partner_id.ids)

            ticket._portal_ensure_token()

        # apply SLA
        tickets.sudo()._sla_apply()

        return tickets

    def write(self, vals):
        # we set the assignation date (assign_date) to now for tickets that are being assigned for the first time
        # same thing for the closing date
        assigned_tickets = closed_tickets = self.browse()
        if vals.get('user_id'):
            assigned_tickets = self.filtered(lambda ticket: not ticket.assign_date)

        if vals.get('stage_id'):
            if self.env['helpdesk.stage'].browse(vals.get('stage_id')).fold:
                closed_tickets = self.filtered(lambda ticket: not ticket.close_date)
            else:  # auto reset the 'closed_by_partner' flag
                vals['closed_by_partner'] = False
                vals['close_date'] = False

        now = fields.Datetime.now()

        # update last stage date when changing stage
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = now
            if 'kanban_state' not in vals:
                vals['kanban_state'] = 'normal'

        res = super(HelpdeskTicket, self - assigned_tickets - closed_tickets).write(vals)
        res &= super(HelpdeskTicket, assigned_tickets - closed_tickets).write(dict(vals, **{
            'assign_date': now,
        }))
        res &= super(HelpdeskTicket, closed_tickets - assigned_tickets).write(dict(vals, **{
            'close_date': now,
            'oldest_unanswered_customer_message_date': False,
        }))
        res &= super(HelpdeskTicket, assigned_tickets & closed_tickets).write(dict(vals, **{
            'assign_date': now,
            'close_date': now,
        }))

        if vals.get('partner_id'):
            self.message_subscribe([vals['partner_id']])

        # SLA business
        sla_triggers = self._sla_reset_trigger()
        if any(field_name in sla_triggers for field_name in vals.keys()):
            self.sudo()._sla_apply(keep_reached=True)
        if 'stage_id' in vals:
            self.sudo()._sla_reach(vals['stage_id'])

        if 'stage_id' in vals and self.env['helpdesk.stage'].browse(vals['stage_id']).fold:
            odoobot_partner_id = self.env['ir.model.data']._xmlid_to_res_id('base.partner_root')
            for ticket in self:
                exceeded_hours = ticket.sla_status_ids.mapped('exceeded_hours')
                if exceeded_hours:
                    min_hours = min([hours for hours in exceeded_hours if hours > 0], default=min(exceeded_hours))
                    message = _("This ticket was successfully closed %s hours before its SLA deadline.", round(abs(min_hours))) if min_hours < 0 \
                        else _("This ticket was closed %s hours after its SLA deadline.", round(min_hours))
                    ticket.message_post(body=message, subtype_xmlid="mail.mt_note", author_id=odoobot_partner_id)
        return res

    def copy(self, default=None):
        default = dict(default or {})
        if not default.get('name'):
            default['name'] = _("%s (copy)", self.name)
        return super().copy(default)

    def _unsubscribe_portal_users(self):
        self.message_unsubscribe(partner_ids=self.message_partner_ids.filtered('user_ids.share').ids)

    # ------------------------------------------------------------
    # Actions and Business methods
    # ------------------------------------------------------------

    @api.model
    def _sla_reset_trigger(self):
        """ Get the list of field for which we have to reset the SLAs (regenerate) """
        return ['team_id', 'priority', 'ticket_type_id', 'tag_ids', 'partner_id']

    def _sla_apply(self, keep_reached=False):
        """ Apply SLA to current tickets: erase the current SLAs, then find and link the new SLAs to each ticket.
            Note: transferring ticket to a team "not using SLA" (but with SLAs defined), SLA status of the ticket will be
            erased but nothing will be recreated.
            :returns recordset of new helpdesk.sla.status applied on current tickets
        """
        # get SLA to apply
        sla_per_tickets = self._sla_find()

        # generate values of new sla status
        sla_status_value_list = []
        for tickets, slas in sla_per_tickets.items():
            sla_status_value_list += tickets._sla_generate_status_values(slas, keep_reached=keep_reached)

        sla_status_to_remove = self.mapped('sla_status_ids')
        if keep_reached:  # keep only the reached one to avoid losing reached_date info
            sla_status_to_remove = sla_status_to_remove.filtered(lambda status: not status.reached_datetime)

        # unlink status and create the new ones in 2 operations
        sla_status_to_remove.unlink()
        return self.env['helpdesk.sla.status'].create(sla_status_value_list)

    def _sla_find_extra_domain(self):
        self.ensure_one()
        return [
            '|', '|', ('partner_ids', 'parent_of', self.partner_id.ids), ('partner_ids', 'child_of', self.partner_id.ids), ('partner_ids', '=', False)
        ]

    def _sla_find(self):
        """ Find the SLA to apply on the current tickets
            :returns a map with the tickets linked to the SLA to apply on them
            :rtype : dict {<helpdesk.ticket>: <helpdesk.sla>}
        """
        tickets_map = {}
        sla_domain_map = {}

        def _generate_key(ticket):
            """ Return a tuple identifying the combinaison of field determining the SLA to apply on the ticket """
            fields_list = self._sla_reset_trigger()
            key = list()
            for field_name in fields_list:
                if ticket._fields[field_name].type == 'many2one':
                    key.append(ticket[field_name].id)
                else:
                    key.append(ticket[field_name])
            return tuple(key)

        for ticket in self:
            if ticket.team_id.use_sla:  # limit to the team using SLA
                key = _generate_key(ticket)
                # group the ticket per key
                tickets_map.setdefault(key, self.env['helpdesk.ticket'])
                tickets_map[key] |= ticket
                # group the SLA to apply, by key
                if key not in sla_domain_map:
                    sla_domain_map[key] = expression.AND([[
                        ('team_id', '=', ticket.team_id.id), ('priority', '=', ticket.priority),
                        ('stage_id.sequence', '>=', ticket.stage_id.sequence),
                        '|', ('ticket_type_ids', 'in', ticket.ticket_type_id.ids), ('ticket_type_ids', '=', False)], ticket._sla_find_extra_domain()])

        result = {}
        for key, tickets in tickets_map.items():  # only one search per ticket group
            domain = sla_domain_map[key]
            slas = self.env['helpdesk.sla'].search(domain)
            result[tickets] = slas.filtered(lambda s: not s.tag_ids or (tickets.tag_ids & s.tag_ids))  # SLA to apply on ticket subset
        return result

    def _sla_generate_status_values(self, slas, keep_reached=False):
        """ Return the list of values for given SLA to be applied on current ticket """
        status_to_keep = dict.fromkeys(self.ids, list())

        # generate the map of status to keep by ticket only if requested
        if keep_reached:
            for ticket in self:
                for status in ticket.sla_status_ids:
                    if status.reached_datetime:
                        status_to_keep[ticket.id].append(status.sla_id.id)

        # create the list of value, and maybe exclude the existing ones
        result = []
        for ticket in self:
            for sla in slas:
                if not (keep_reached and sla.id in status_to_keep[ticket.id]):
                    result.append({
                        'ticket_id': ticket.id,
                        'sla_id': sla.id,
                        'reached_datetime': fields.Datetime.now() if ticket.stage_id == sla.stage_id else False # in case of SLA on first stage
                    })

        return result

    def _sla_reach(self, stage_id):
        """ Flag the SLA status of current ticket for the given stage_id as reached, and even the unreached SLA applied
            on stage having a sequence lower than the given one.
        """
        stage = self.env['helpdesk.stage'].browse(stage_id)
        stages = self.env['helpdesk.stage'].search([('sequence', '<=', stage.sequence), ('team_ids', 'in', self.mapped('team_id').ids)])  # take previous stages
        sla_status = self.env['helpdesk.sla.status'].search([('ticket_id', 'in', self.ids)])
        sla_not_reached = sla_status.filtered(lambda sla: not sla.reached_datetime and sla.sla_stage_id in stages)
        sla_not_reached.write({'reached_datetime': fields.Datetime.now()})
        (sla_status - sla_not_reached).filtered(lambda x: x.sla_stage_id not in stages).write({'reached_datetime': False})

    def action_open_helpdesk_ticket(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk.helpdesk_ticket_action_main_tree")
        action.update({
            'domain': [('id', '!=', self.id), ('id', 'in', self.partner_ticket_ids.ids)],
            'context': {
                **ast.literal_eval(action.get('context', {})),
                'create': False,
            },
        })
        return action

    def action_open_ratings(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('helpdesk.rating_rating_action_helpdesk')
        if self.rating_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.rating_ids[0].id,
                'views': [(view_id, view_type) for view_id, view_type in action['views'] if view_type == 'form'],
            })
        return action

    # ------------------------------------------------------------
    # Messaging API
    # ------------------------------------------------------------

    #DVE FIXME: if partner gets created when sending the message it should be set as partner_id of the ticket.
    def _message_get_suggested_recipients(self):
        recipients = super(HelpdeskTicket, self)._message_get_suggested_recipients()
        try:
            for ticket in self:
                if ticket.partner_id and ticket.partner_id.email:
                    ticket._message_add_suggested_recipient(recipients, partner=ticket.partner_id, reason=_('Customer'))
                elif ticket.partner_email:
                    ticket._message_add_suggested_recipient(recipients, email=ticket.partner_email, reason=_('Customer Email'))
        except AccessError:  # no read access rights -> just ignore suggested recipients because this implies modifying followers
            pass
        return recipients

    def _get_customer_information(self):
        email_normalized_to_values = super()._get_customer_information()
        Partner = self.env['res.partner']

        for record in self.filtered('partner_email'):
            email_normalized = tools.email_normalize(record.partner_email)
            if not email_normalized:
                continue
            values = email_normalized_to_values.setdefault(email_normalized, {})
            values.update({
                'name': record.partner_name or tools.parse_contact_from_email(record.partner_email)[0] or record.partner_email,
                'phone': record.partner_phone,
            })
        return email_normalized_to_values

    def _ticket_email_split(self, msg):
        email_list = tools.email_split((msg.get('to') or '') + ',' + (msg.get('cc') or ''))
        # check left-part is not already an alias
        return [
            x for x in email_list
            if x.split('@')[0] not in self.mapped('team_id.alias_name')
        ]

    @api.model
    def message_new(self, msg, custom_values=None):
        values = dict(custom_values or {}, partner_email=msg.get('from'), partner_name=msg.get('from'), partner_id=msg.get('author_id'))
        ticket = super(HelpdeskTicket, self.with_context(mail_notify_author=True)).message_new(msg, custom_values=values)
        thread_context = self.env['mail.thread']
        if ticket.company_id:
            thread_context = thread_context.with_context(default_company_id=ticket.company_id)
        partner_ids = [x.id for x in thread_context._mail_find_partner_from_emails(ticket._ticket_email_split(msg), records=ticket, force_create=True) if x]
        customer_ids = [p.id for p in thread_context._mail_find_partner_from_emails(tools.email_split(values['partner_email']), records=ticket, force_create=True) if p]
        partner_ids += customer_ids
        if customer_ids and not values.get('partner_id'):
            ticket.partner_id = customer_ids[0]
        if partner_ids:
            ticket.message_subscribe(partner_ids)
        return ticket

    def message_update(self, msg, update_vals=None):
        partner_ids = [x.id for x in self.env['mail.thread']._mail_find_partner_from_emails(self._ticket_email_split(msg), records=self) if x]
        if partner_ids:
            self.message_subscribe(partner_ids)
        return super(HelpdeskTicket, self).message_update(msg, update_vals=update_vals)

    def _message_compute_subject(self):
        """ Override the display name by the actual name field for communication."""
        self.ensure_one()
        return self.name

    def _message_post_after_hook(self, message, msg_vals):
        if not self.partner_email:
            return super()._message_post_after_hook(message, msg_vals)

        if self.partner_id and not self.partner_id.email:
            self.partner_id.email = self.partner_email

        if not self.partner_id:
            # we consider that posting a message with a specified recipient (not a follower, a specific one)
            # on a document without customer means that it was created through the chatter using
            # suggested recipients. This heuristic allows to avoid ugly hacks in JS.
            email_normalized = tools.email_normalize(self.partner_email)
            new_partner = message.partner_ids.filtered(
                lambda partner: partner.email == self.partner_email or (email_normalized and partner.email_normalized == email_normalized)
            )
            if new_partner:
                if new_partner[0].email_normalized:
                    email_domain = ('partner_email', 'in', [new_partner[0].email, new_partner[0].email_normalized])
                else:
                    email_domain = ('partner_email', '=', new_partner[0].email)
                self.search([
                    ('partner_id', '=', False), email_domain,
                ]).write({'partner_id': new_partner[0].id})
        # use the sanitized body of the email from the message thread to populate the ticket's description
        if not self.description and message.subtype_id == self._creation_subtype() and tools.email_normalize(self.partner_email) == tools.email_normalize(message.email_from):
            self.description = message.body
        return super(HelpdeskTicket, self)._message_post_after_hook(message, msg_vals)

    def _track_template(self, changes):
        res = super(HelpdeskTicket, self)._track_template(changes)
        ticket = self[0]
        if 'stage_id' in changes and ticket.stage_id.template_id and ticket.partner_email and (
            not self.env.user.partner_id or not ticket.partner_id or ticket.partner_id != self.env.user.partner_id
            or self.env.user._is_portal() or ticket._context.get('mail_notify_author')
        ):
            res['stage_id'] = (ticket.stage_id.template_id, {
                'auto_delete_keep_log': False,
                'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'mail.mail_notification_light'
            }
        )
        return res

    def _creation_subtype(self):
        return self.env.ref('helpdesk.mt_ticket_new')

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'stage_id' in init_values:
            return self.env.ref('helpdesk.mt_ticket_stage')
        return super(HelpdeskTicket, self)._track_subtype(init_values)

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        """
        Give access button to portal and portal customers.
        If they are notified they should probably have access to the document.
        """
        return super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )

    def _notify_get_reply_to(self, default=None):
        """ Override to set alias of tickets to their team if any. """
        aliases = self.mapped('team_id').sudo()._notify_get_reply_to(default=default)
        res = {ticket.id: aliases.get(ticket.team_id.id) for ticket in self}
        leftover = self.filtered(lambda rec: not rec.team_id)
        if leftover:
            res.update(super(HelpdeskTicket, leftover)._notify_get_reply_to(default=default))
        return res

    # ------------------------------------------------------------
    # Rating Mixin
    # ------------------------------------------------------------

    def _rating_apply_get_default_subtype_id(self):
        return self.env['ir.model.data']._xmlid_to_res_id("helpdesk.mt_ticket_rated")

    def _rating_get_parent_field_name(self):
        return 'team_id'

    # ---------------------------------------------------
    # Mail gateway
    # ---------------------------------------------------

    def _mail_get_message_subtypes(self):
        res = super()._mail_get_message_subtypes()
        if len(self) == 1 and self.team_id:
            team = self.team_id
            optional_subtypes = [('use_credit_notes', self.env.ref('helpdesk.mt_ticket_refund_status')),
                                 ('use_product_returns', self.env.ref('helpdesk.mt_ticket_return_status')),
                                 ('use_product_repairs', self.env.ref('helpdesk.mt_ticket_repair_status'))]
            for field, subtype in optional_subtypes:
                if not team[field] and subtype in res:
                    res -= subtype
        return res
