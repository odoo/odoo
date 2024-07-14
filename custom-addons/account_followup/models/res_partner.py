# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast
from collections import defaultdict
import logging

from odoo import api, fields, models, _
from odoo.tools.misc import format_date
from datetime import datetime, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    followup_next_action_date = fields.Date(
        string='Next reminder',
        copy=False,
        company_dependent=True,
        help="""The date before which no follow-up action should be taken.
                You can set it manually if desired but it is automatically set when follow-ups are processed.
                The date is computed according to the following rules (depending on the follow-up levels):
                - default -> next date set in {next level delay - current level delay} days
                - if no next level -> next date set in {current level delay - previous level delay} days
                - if no next level AND no previous level -> next date set in {current level delay} days
                - if no level defined at all -> next date never automatically set""",
    )

    # readonly=False in order to be able to edit it directly in the view form, without having to click on 'Edit'
    # It's mainly used for usability purposes to easily include/exclude unreconciled move lines
    unreconciled_aml_ids = fields.One2many('account.move.line', compute='_compute_total_due', readonly=False)

    unpaid_invoice_ids = fields.One2many('account.move', compute='_compute_unpaid_invoices')
    unpaid_invoices_count = fields.Integer(compute='_compute_unpaid_invoices')
    total_due = fields.Monetary(
        compute='_compute_total_due',
        groups='account.group_account_readonly,account.group_account_invoice')
    total_overdue = fields.Monetary(
        compute='_compute_total_due',
        groups='account.group_account_readonly,account.group_account_invoice')
    followup_status = fields.Selection(
        [('in_need_of_action', 'In need of action'), ('with_overdue_invoices', 'With overdue invoices'), ('no_action_needed', 'No action needed')],
        compute='_compute_followup_status',
        string='Follow-up Status',
        search='_search_status',
        groups='account.group_account_readonly,account.group_account_invoice',
    )
    followup_line_id = fields.Many2one(
        comodel_name='account_followup.followup.line',
        string="Follow-up Level",
        compute='_compute_followup_status',
        inverse='_set_followup_line_on_unreconciled_amls',
        search='_search_followup_line',
        groups='account.group_account_readonly,account.group_account_invoice',
    )
    followup_reminder_type = fields.Selection([('automatic', 'Automatic'), ('manual', 'Manual')], string="Reminders", default='automatic')
    type = fields.Selection(
        selection_add=[('followup', 'Follow-up Address'), ('other',)],
        help="- Contact: Use this to organize the contact details of employees of a given company (e.g. CEO, CFO, ...).\n"
             "- Invoice Address: Preferred address for all invoices. Selected by default when you invoice an order that belongs to this company.\n"
             "- Delivery Address: Preferred address for all deliveries. Selected by default when you deliver an order that belongs to this company.\n"
             "- Private: Private addresses are only visible by authorized users and contain sensitive data (employee home addresses, ...).\n"
             "- Follow-up Address: Preferred address for follow-up reports. Selected by default when you send reminders about overdue invoices.\n"
             "- Other: Other address for the company (e.g. subsidiary, ...)")
    followup_responsible_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsible',
        help="The responsible assigned to manual followup activities, if defined in the level.",
        tracking=True,
        copy=False,
        company_dependent=True,
        groups='account.group_account_readonly,account.group_account_invoice',
    )

    @property
    def _complete_name_displayed_types(self):
        return super()._complete_name_displayed_types + ('followup',)

    def _search_status(self, operator, value):
        """
        Compute the search on the field 'followup_status'
        """
        if isinstance(value, str):
            value = [value]
        if operator not in ('in', '=') or not value:
            return []
        value = [v for v in value if v in ['in_need_of_action', 'with_overdue_invoices', 'no_action_needed']]

        followup_data = self._query_followup_data(all_partners=True)

        return [('id', 'in', [
            d['partner_id']
            for d in followup_data.values()
            if d['followup_status'] in value
        ])]

    def _search_followup_line(self, operator, value):
        company_domain = [('company_id', 'parent_of', self.env.company.id)]
        if isinstance(value, str):
            domain = [('name', operator, value)]
        elif isinstance(value, (int, list, tuple)):
            domain = [('id', operator, value)]

        line_ids = set(self.env['account_followup.followup.line'].search(domain+company_domain).ids)

        followup_data = self._query_followup_data(all_partners=True)

        return [('id', 'in', [
            d['partner_id']
            for d in followup_data.values()
            if d['followup_line_id'] in line_ids
        ])]

    @api.depends('unreconciled_aml_ids', 'followup_next_action_date')
    @api.depends_context('company', 'allowed_company_ids')
    def _compute_followup_status(self):
        all_data = self._query_followup_data()
        for partner in self:
            partner_data = all_data.get(partner._origin.id, {'followup_status': 'no_action_needed', 'followup_line_id': False})
            partner.followup_status = partner_data['followup_status']
            partner.followup_line_id = partner_data['followup_line_id']

    def _compute_unpaid_invoices(self):
        for partner in self:
            unpaid_receivable_lines = self.env['account.move.line'].search([
                ('company_id', 'child_of', self.env.company.id),
                ('move_id.commercial_partner_id', '=', partner.id),
                ('parent_state', '=', 'posted'),
                ('move_id.payment_state', 'in', ('not_paid', 'partial')),
                ('move_id.move_type', 'in', self.env['account.move'].get_sale_types()),
                ('account_id.account_type', '=', 'asset_receivable'),
            ])
            unpaid_invoices = unpaid_receivable_lines.move_id
            partner.unpaid_invoice_ids = unpaid_invoices
            partner.unpaid_invoices_count = len(unpaid_invoices)

    def action_view_unpaid_invoices(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action['domain'] = [('id', 'in', self.unpaid_invoice_ids.ids)]
        action['context'] = {
            'default_move_type': 'out_invoice',
            'move_type': 'out_invoice',
            'journal_type': 'sale',
            'partner_id': self.id
        }
        return action

    def action_open_unreconciled_partner(self):
        action_values = self.env["ir.actions.actions"]._for_xml_id("account_accountant.action_move_line_posted_unreconciled")
        domain = ast.literal_eval(action_values['domain'])
        domain.append(('partner_id', 'in', self.ids))
        action_values['domain'] = domain
        return action_values

    @api.depends('invoice_ids')
    @api.depends_context('company', 'allowed_company_ids')
    def _compute_total_due(self):
        due_data = defaultdict(float)
        overdue_data = defaultdict(float)
        unreconciled_aml_ids = defaultdict(list)
        for overdue, partner, blocked, amount_residual_sum, aml_ids in self.env['account.move.line']._read_group(
            domain=self._get_unreconciled_aml_domain(),
            groupby=['followup_overdue', 'partner_id', 'blocked'],
            aggregates=['amount_residual:sum', 'id:array_agg'],
        ):
            unreconciled_aml_ids[partner] += aml_ids
            if not blocked:
                due_data[partner] += amount_residual_sum
                if overdue:
                    overdue_data[partner] += amount_residual_sum

        for partner in self:
            partner.total_due = due_data.get(partner, 0.0)
            partner.total_overdue = overdue_data.get(partner, 0.0)
            partner.unreconciled_aml_ids = self.env['account.move.line'].browse(unreconciled_aml_ids.get(partner, []))

    def _set_followup_line_on_unreconciled_amls(self):
        today = fields.Date.context_today(self)
        for partner in self:
            current_followup_line = partner.followup_line_id
            previous_followup_line = self.env['account_followup.followup.line'].search([('delay', '<', current_followup_line.delay), ('company_id', 'parent_of', self.env.company.id)], order='delay desc', limit=1)
            for unreconciled_aml in partner.unreconciled_aml_ids:
                if not unreconciled_aml.blocked:
                    unreconciled_aml.followup_line_id = previous_followup_line
                    # When a specific followup line is manually selected, we consider the followup as processed
                    unreconciled_aml.last_followup_date = today

    def _get_unreconciled_aml_domain(self):
        return [
            ('reconciled', '=', False),
            ('account_id.deprecated', '=', False),
            ('account_id.account_type', '=', 'asset_receivable'),
            ('parent_state', '=', 'posted'),
            ('partner_id', 'in', self.ids),
            ('company_id', 'child_of', self.env.company.id),
        ]

    def _get_followup_responsible(self):
        self.ensure_one()

        responsible_type = self.followup_line_id.activity_default_responsible_type
        if responsible_type == 'account_manager' and self.user_id:
            return self.user_id

        most_delayed_aml = self._included_unreconciled_aml_max_followup().get('most_delayed_aml')
        if responsible_type == 'salesperson' and most_delayed_aml and most_delayed_aml.move_id.invoice_user_id:
            return most_delayed_aml.move_id.invoice_user_id

        if self.followup_responsible_id:
            return self.followup_responsible_id

        if self.user_id:
            return self.user_id

        if most_delayed_aml and most_delayed_aml.move_id.invoice_user_id:
            return most_delayed_aml.move_id.invoice_user_id

        return self.env.user

    def _get_all_followup_contacts(self):
        """ Returns every contact of type 'followup' in the children of self.
        If no followup contacts are found, use the billing address
        and default to contact if there isn't any for invoice
        """
        self.ensure_one()
        followup_contacts = self.child_ids.filtered(lambda partner: partner.type == 'followup')
        if not followup_contacts:
            followup_contacts = self.env['res.partner'].browse(self.address_get(['invoice'])['invoice'])
        return followup_contacts

    def _included_unreconciled_aml_max_followup(self):
        """ Computes the maximum delay in days and the highest level of followup (followup line with highest delay) of all the unreconciled amls included.
        Also returns the delay for the next level (after the highest_followup_line), the most delayed aml and a boolean specifying if any invoice is overdue.
        :return dict with key/values: most_delayed_aml, max_delay, highest_followup_line, next_followup_delay, has_overdue_invoices
        """
        self.ensure_one()
        today = fields.Date.context_today(self)
        highest_followup_line = None
        most_delayed_aml = self.env['account.move.line']
        first_followup_line = self._get_first_followup_level()
        # Minimum value for delay, will always be smaller than any other delay
        max_delay = first_followup_line.delay - 1
        has_overdue_invoices = False
        for aml in self.unreconciled_aml_ids:
            aml_delay = (today - (aml.date_maturity or aml.date)).days

            is_overdue = aml_delay > 0
            if is_overdue:
                has_overdue_invoices = True

            if self.env.company in aml.company_id.parent_ids and not aml.blocked:
                if aml.followup_line_id and aml.followup_line_id.delay >= (highest_followup_line or first_followup_line).delay:
                    highest_followup_line = aml.followup_line_id
                max_delay = max(max_delay, aml_delay)
                if most_delayed_aml.amount_residual < aml.amount_residual:
                    most_delayed_aml = aml
        followup_lines_info = self._get_followup_lines_info()
        next_followup_delay = None
        if followup_lines_info:
            key = highest_followup_line.id if highest_followup_line else None
            current_followup_line_info = followup_lines_info.get(key)
            next_followup_delay = current_followup_line_info.get('next_delay')
        return {
            'most_delayed_aml': most_delayed_aml,
            'max_delay': max_delay,
            'highest_followup_line': highest_followup_line,
            'next_followup_delay': next_followup_delay,
            'has_overdue_invoices': has_overdue_invoices,
        }

    def _get_invoices_to_print(self, options):
        self.ensure_one()
        if not options:
            options = {}
        invoices_to_print = self._get_included_unreconciled_aml_ids().move_id.filtered(lambda l: l.is_invoice(include_receipts=True))
        if options.get('manual_followup'):
            # For manual reminders, only print invoices with the selected attachments
            return invoices_to_print.filtered(lambda inv: inv.message_main_attachment_id.id in options.get('attachment_ids'))
        return invoices_to_print.filtered(lambda inv: inv.message_main_attachment_id)

    def _get_included_unreconciled_aml_ids(self):
        self.ensure_one()
        return self.unreconciled_aml_ids.filtered(lambda aml: not aml.blocked)

    @api.model
    def _get_first_followup_level(self):
        return self.env['account_followup.followup.line'].search([('company_id', 'parent_of', self.env.company.id)], order='delay asc', limit=1)

    def _update_next_followup_action_date(self, followup_line):
        """Updates the followup_next_action_date of the right account move lines
        """
        self.ensure_one()
        if followup_line:
            next_date = followup_line._get_next_date()
            self.followup_next_action_date = datetime.strftime(next_date, DEFAULT_SERVER_DATE_FORMAT)
            msg = _('Next Reminder Date set to %s', format_date(self.env, self.followup_next_action_date))
            self.message_post(body=msg)

        today = fields.Date.context_today(self)
        previous_levels = self.env['account_followup.followup.line'].search([('delay', '<=', followup_line.delay), ('company_id', '=', self.env.company.id)])
        for aml in self._get_included_unreconciled_aml_ids().filtered('date_maturity'):
            eligible_levels = previous_levels.filtered(lambda level: (today - aml.date_maturity).days >= level.delay)
            if eligible_levels:
                aml.followup_line_id = max(eligible_levels, key=lambda level: level.delay)

    def open_action_followup(self):
        self.ensure_one()
        return {
            'name': _("Overdue Payments for %s", self.display_name),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'views': [[self.env.ref('account_followup.customer_statements_form_view').id, 'form']],
            'res_model': 'res.partner',
            'res_id': self.id,
        }

    def send_followup_email(self, options):
        """
        Send a follow-up report by email to customers in self
        """
        for record in self:
            options['partner_id'] = record.id
            self.env['account.followup.report']._send_email(options)

    def send_followup_sms(self, options):
        """
        Send a follow-up report by sms to customers in self
        """
        for partner in self:
            options['partner_id'] = partner.id
            self.env['account.followup.report']._send_sms(options)

    def get_followup_html(self, options=None):
        """
        Return the content of the follow-up report in HTML
        """
        if options is None:
            options = {}
        options.update({
            'partner_id': self.id,
            'followup_line_id': self.followup_line_id,
        })
        return self.env['account.followup.report'].with_context(print_mode=True, lang=self.lang or self.env.user.lang).get_followup_report_html(options)

    def _get_followup_lines_info(self):
        """ returns the followup plan of the current user's company
        in the form of a dictionary with
         * keys being the different possible lines of followup for account.move.line's (None or IDs of account_followup.followup.line)
         * values being a dict of 2 elements:
           - 'next_followup_line_id': the followup ID of the next followup line
           - 'next_delay': the delay in days of the next followup line
        """
        followup_lines = self.env['account_followup.followup.line'].search([('company_id', 'parent_of', self.env.company.id)], order="delay asc")

        previous_line_id = None
        followup_lines_info = {}
        for line in followup_lines:
            delay_in_days = line.delay
            followup_lines_info[previous_line_id] = {
                'next_followup_line_id': line.id,
                'next_delay': delay_in_days,
            }
            previous_line_id = line.id
        if previous_line_id:
            followup_lines_info[previous_line_id] = {
                'next_followup_line_id': previous_line_id,
                'next_delay': delay_in_days,
            }
        return followup_lines_info

    def _query_followup_data(self, all_partners=False):
        self.env['account.move.line'].check_access_rights('read')
        self.env['account.move.line'].flush_model()
        self.env['res.partner'].flush_model()
        self.env['ir.property'].flush_model()
        self.env['account_followup.followup.line'].flush_model()

        # Put the data in a cache in the database to avoid running costly query multiple times in same transaction.
        # Only do it if the table doesn't exist yet.
        self.env.cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name='followup_data_cache'")
        is_cached = self.env.cr.fetchone()
        if all_partners:
            if not is_cached:
                query, params = self._get_followup_data_query()
                self.env.cr.execute(f"""
                    CREATE TEMP TABLE followup_data_cache (partner_id int4, followup_line_id int4, followup_status varchar) ON COMMIT DROP;
                    INSERT INTO followup_data_cache {query}
                """, params)
            self.env.cr.execute('SELECT * FROM followup_data_cache')
        else:
            if not self.ids:
                return {}
            elif is_cached:
                query, params = "SELECT * FROM followup_data_cache WHERE partner_id IN %s", [tuple(self.ids)]
            else:
                query, params = self._get_followup_data_query(self.ids)
            self.env.cr.execute(query, params)
        result = {r['partner_id']: r for r in self.env.cr.dictfetchall()}
        return result

    def _get_followup_data_query(self, partner_ids=None):
        self.env['ir.property'].flush_model()
        return f"""
            SELECT partner.id as partner_id,
                   ful.id as followup_line_id,
                   CASE WHEN partner.balance <= 0 THEN 'no_action_needed'
                        WHEN in_need_of_action_aml.id IS NOT NULL AND (prop_date.value_datetime IS NULL OR prop_date.value_datetime::date <= %(current_date)s) THEN 'in_need_of_action'
                        WHEN exceeded_unreconciled_aml.id IS NOT NULL THEN 'with_overdue_invoices'
                        ELSE 'no_action_needed' END as followup_status
            FROM (
          SELECT partner.id,
                 MAX(COALESCE(next_ful.delay, ful.delay)) as followup_delay,
                 SUM(aml.balance) as balance
            FROM res_partner partner
            JOIN account_move_line aml ON aml.partner_id = partner.id
            JOIN account_account account ON account.id = aml.account_id
       LEFT JOIN account_followup_followup_line ful ON ful.id = aml.followup_line_id
       LEFT JOIN account_followup_followup_line next_ful ON next_ful.id = (
                    SELECT next_ful.id
                      FROM account_followup_followup_line next_ful
                     WHERE next_ful.delay > COALESCE(ful.delay, %(min_delay)s - 1)
                       AND next_ful.company_id = %(root_company_id)s
                  ORDER BY next_ful.delay ASC
                     LIMIT 1
                 )
           WHERE account.deprecated IS NOT TRUE
             AND account.account_type = 'asset_receivable'
             AND aml.parent_state = 'posted'
             AND aml.reconciled IS NOT TRUE
             AND aml.blocked IS FALSE
             AND aml.company_id = ANY(%(company_ids)s)
             {"" if partner_ids is None else "AND aml.partner_id IN %(partner_ids)s"}
        GROUP BY partner.id
            ) partner
            LEFT JOIN account_followup_followup_line ful ON ful.delay = partner.followup_delay AND ful.company_id = %(root_company_id)s
            -- Get the followup status data
            LEFT OUTER JOIN LATERAL (
                SELECT line.id
                  FROM account_move_line line
                  JOIN account_account account ON line.account_id = account.id
             LEFT JOIN account_followup_followup_line ful ON ful.id = line.followup_line_id
                 WHERE line.partner_id = partner.id
                   AND account.account_type = 'asset_receivable'
                   AND account.deprecated IS NOT TRUE
                   AND line.parent_state = 'posted'
                   AND line.reconciled IS NOT TRUE
                   AND line.balance > 0
                   AND line.blocked IS FALSE
                   AND line.company_id = ANY(%(company_ids)s)
                   AND COALESCE(ful.delay, %(min_delay)s - 1) <= partner.followup_delay
                   AND COALESCE(line.date_maturity, line.date) + COALESCE(ful.delay, %(min_delay)s - 1) < %(current_date)s
                 LIMIT 1
            ) in_need_of_action_aml ON true
            LEFT OUTER JOIN LATERAL (
                SELECT line.id
                  FROM account_move_line line
                  JOIN account_account account ON line.account_id = account.id
                 WHERE line.partner_id = partner.id
                   AND account.account_type = 'asset_receivable'
                   AND account.deprecated IS NOT TRUE
                   AND line.parent_state = 'posted'
                   AND line.reconciled IS NOT TRUE
                   AND line.balance > 0
                   AND line.blocked IS FALSE
                   AND line.company_id = ANY(%(company_ids)s)
                   AND COALESCE(line.date_maturity, line.date) < %(current_date)s
                 LIMIT 1
            ) exceeded_unreconciled_aml ON true
            LEFT OUTER JOIN ir_property prop_date ON prop_date.res_id = CONCAT('res.partner,', partner.id)
                                                 AND prop_date.name = 'followup_next_action_date'
                                                 AND prop_date.company_id = %(root_company_id)s
        """, {
            'company_ids': self.env.company.search([('id', 'child_of', self.env.company.id)]).ids,
            'root_company_id': self.env.company.root_id.id,
            'partner_ids': tuple(partner_ids or []),
            'current_date': fields.Date.context_today(self),  # Allow mocking the current day for testing purpose.
            'min_delay': self._get_first_followup_level().delay or 0,
        }

    def _send_followup(self, options):
        """ Send the follow-up to the partner, depending on selected options.
        Can be overridden to include more ways of sending the follow-up.
        """
        self.ensure_one()
        followup_line = options.get('followup_line')
        if options.get('email', followup_line.send_email):
            self.send_followup_email(options)
        if options.get('sms', followup_line.send_sms):
            self.send_followup_sms(options)

    def _execute_followup_partner(self, options=None):
        """ Execute the actions to do with follow-ups for this partner (apart from printing).
        This is either called when processing the follow-ups manually (wizard), or automatically (cron).
        Automatic follow-ups can also be triggered manually with *action_manually_process_automatic_followups*.
        When processing automatically, options is None.

        Returns True if any action was processed, False otherwise
        """
        self.ensure_one()
        if options is None:
            options = {}
        if options.get('manual_followup', self.followup_status == 'in_need_of_action'):
            followup_line = self.followup_line_id or self._get_first_followup_level()

            if followup_line.create_activity:
                # log a next activity for today
                self.activity_schedule(
                    activity_type_id=followup_line.activity_type_id and followup_line.activity_type_id.id or self._default_activity_type().id,
                    note=followup_line.activity_note,
                    summary=followup_line.activity_summary,
                    user_id=(self._get_followup_responsible()).id
                )

            self._update_next_followup_action_date(followup_line)

            if not options.get('join_invoices', followup_line.join_invoices):
                options['attachment_ids'] = []

            self._send_followup(options={'followup_line': followup_line, **options})

            return True
        return False

    def execute_followup(self, options):
        """ Execute the actions to do with follow-ups for this partner.
        This is called when processing the follow-ups manually, via the wizard.

        options is a dictionary containing at least the following information:
            - 'partner_id': id of partner (self)
            - 'email': boolean to trigger the sending of email or not
            - 'email_subject': subject of email
            - 'followup_contacts': partners (contacts) to send the followup to
            - 'body': email body
            - 'attachment_ids': invoice attachments to join to email/letter
            - 'sms': boolean to trigger the sending of sms or not
            - 'sms_body': sms body
            - 'print': boolean to trigger the printing of pdf letter or not
            - 'manual_followup': boolean to indicate whether this followup is triggered via the manual reminder wizard
        """
        self.ensure_one()
        to_print = self._execute_followup_partner(options=options)
        if options.get('print') and to_print:
            return self.env['account.followup.report']._print_followup_letter(self, options)

    def _create_followup_missing_information_wizard(self):
        """ Returns a wizard containing all the partners with missing information.
        """

        return {
            'type': 'ir.actions.act_window',
            'name': _("Missing information"),
            'view_mode': 'form',
            'res_model': 'account_followup.missing.information.wizard',
            'target': 'new',
            'context': {'default_partner_ids': self.ids},
        }

    def _has_missing_followup_info(self):
        self.ensure_one()

        followup_contacts = self._get_all_followup_contacts() or self

        if self.followup_line_id.send_email and not any(followup_contacts.mapped('email')):
            return True

        if self.followup_line_id.send_sms and not (any(followup_contacts.mapped('mobile'))
                                            or any(followup_contacts.mapped('phone'))):
            return True
        return False

    def action_manually_process_automatic_followups(self):
        partners_with_missing_info = self.env['res.partner']

        for partner in self:
            if partner.followup_status != 'in_need_of_action':
                continue

            # Skip partner with missing info.
            if partner._has_missing_followup_info():
                partners_with_missing_info |= partner
                continue

            partner._execute_followup_partner()

        # If one or more partners are missing information, open a wizard listing them.
        if partners_with_missing_info:
            return partners_with_missing_info._create_followup_missing_information_wizard()

    def _cron_execute_followup_company(self):
        followup_data = self._query_followup_data(all_partners=True)
        in_need_of_action = self.env['res.partner'].browse([d['partner_id'] for d in followup_data.values() if d['followup_status'] == 'in_need_of_action'])
        in_need_of_action_auto = in_need_of_action.filtered(lambda p: p.followup_line_id.auto_execute and p.followup_reminder_type == 'automatic')
        for partner in in_need_of_action_auto:
            try:
                partner._execute_followup_partner()
            except UserError as e:
                # followup may raise exception due to configuration issues
                # i.e. partner missing email
                _logger.warning(e, exc_info=True)

    def _cron_execute_followup(self):
        for company in self.env["res.company"].search([]):
            # Since the cache is done by database and not by company, we need to invalidate in this special case
            # where the context is changing in the same transaction
            self.env.cr.execute("DROP TABLE IF EXISTS followup_data_cache")
            self.with_context(allowed_company_ids=company.ids)._cron_execute_followup_company()
