import ast
import logging

from collections import defaultdict
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, SQL
from odoo.tools.misc import format_date, get_lang

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    followup_next_action_date = fields.Date(
        string='Next reminder',
        copy=False,
        company_dependent=True,
        help='''No follow-up action will be taken before this date.
                Sending a reminder will set this date depending on the levels configuration, and you can change it manually.''',
    )

    # readonly=False in order to be able to edit it directly in the view form, without having to click on 'Edit'
    # It's mainly used for usability purposes to easily include/exclude unreconciled move lines
    unreconciled_aml_ids = fields.One2many('account.move.line', compute='_compute_total_due', readonly=False)

    unpaid_invoice_ids = fields.One2many('account.move', compute='_compute_unpaid_invoices')
    unpaid_invoices_count = fields.Integer(compute='_compute_unpaid_invoices')
    # These two fields are meant to receive the due and overdue amounts, including asset_receivable AND liability_payable accounts
    # In opposition to the total_due and total_overdue fields which only take into account asset_receivable accounts
    # To be renamed in master
    total_all_due = fields.Monetary(
        compute='_compute_total_due',
        groups='account.group_account_readonly,account.group_account_invoice')
    total_all_overdue = fields.Monetary(
        compute='_compute_total_due',
        groups='account.group_account_readonly,account.group_account_invoice')
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
    type = fields.Selection(selection_add=[('followup', 'Follow-up Address'), ('other',)])
    followup_responsible_id = fields.Many2one(
        comodel_name='res.users',
        string='Responsible',
        help="The responsible assigned to manual followup activities, if defined in the level.",
        tracking=True,
        copy=False,
        company_dependent=True,
        groups='account.group_account_readonly,account.group_account_invoice',
    )
    has_moves = fields.Boolean(compute='_compute_has_moves')

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
        partners_unpaid_receivable_lines = self.env['account.move.line'].search([
            ('company_id', 'child_of', self.env.company.id),
            ('move_id.commercial_partner_id', 'in', self.ids),
            ('parent_state', '=', 'posted'),
            ('move_id.payment_state', 'in', ('not_paid', 'partial')),
            ('move_id.move_type', 'in', self.env['account.move'].get_sale_types()),
            ('account_id.account_type', '=', 'asset_receivable'),
        ]).grouped(lambda line: line.move_id.commercial_partner_id.id)
        for partner in self:
            unpaid_receivable_lines = partners_unpaid_receivable_lines.get(partner.id, self.env['account.move.line'])
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

    def action_open_overdue_entries(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Overdue Invoices"),
            'res_model': 'account.move',
            'domain': [('commercial_partner_id', '=', self.id), ('move_type', 'in', ('out_invoice', 'out_refund'))],
            'view_mode': 'list,form',
            'context': {'search_default_late': True},
        }

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
        receivable_due_data = defaultdict(float)
        receivable_overdue_data = defaultdict(float)
        unreconciled_aml_ids = defaultdict(list)
        for account_type, overdue, partner, amount_residual_sum, aml_ids in self.env['account.move.line']._read_group(
            domain=self._get_unreconciled_aml_domain(),
            groupby=['account_type', 'followup_overdue', 'partner_id'],
            aggregates=['amount_residual:sum', 'id:array_agg'],
        ):
            if account_type == 'asset_receivable':
                unreconciled_aml_ids[partner] += aml_ids
                receivable_due_data[partner] += amount_residual_sum
                if overdue:
                    receivable_overdue_data[partner] += amount_residual_sum
            due_data[partner] += amount_residual_sum
            if overdue:
                overdue_data[partner] += amount_residual_sum

        for partner in self:
            partner.total_all_due = due_data.get(partner, 0.0)
            partner.total_all_overdue = overdue_data.get(partner, 0.0)
            partner.total_due = receivable_due_data.get(partner, 0.0)
            partner.total_overdue = receivable_overdue_data.get(partner, 0.0)
            partner.unreconciled_aml_ids = self.env['account.move.line'].browse(unreconciled_aml_ids.get(partner, []))

    def _set_followup_line_on_unreconciled_amls(self):
        today = fields.Date.context_today(self)
        for partner in self:
            current_followup_line = partner.followup_line_id
            previous_followup_line = self.env['account_followup.followup.line'].search([('delay', '<', current_followup_line.delay), ('company_id', 'parent_of', self.env.company.id)], order='delay desc', limit=1)
            for unreconciled_aml in partner.unreconciled_aml_ids:
                unreconciled_aml.followup_line_id = previous_followup_line

    def _get_unreconciled_aml_domain(self):
        return [
            ('reconciled', '=', False),
            ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
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

        candidates = [
            (responsible_type == 'salesperson' and most_delayed_aml and most_delayed_aml.move_id.invoice_user_id),
            self.followup_responsible_id,
            self.user_id,
            (most_delayed_aml and most_delayed_aml.move_id.invoice_user_id),
        ]
        return next((u for u in candidates if u and u.active), super()._get_followup_responsible())

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
        for aml in self.unreconciled_aml_ids.filtered('date_maturity'):
            aml_delay = (today - aml.date_maturity).days

            is_overdue = aml_delay > 0
            if is_overdue:
                has_overdue_invoices = True

            if self.env.company in aml.company_id.parent_ids:
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
        if not options.get('join_invoices', options.get('followup_line', self.followup_line_id).join_invoices):
            return self.env['account.move']
        invoices_to_print = self.unreconciled_aml_ids.move_id.filtered(lambda l: l.is_invoice(include_receipts=True))
        if options.get('manual_followup'):
            # For manual reminders, only print invoices with the selected attachments
            return invoices_to_print.filtered(lambda inv: inv.invoice_pdf_report_id.id in options.get('attachment_ids', []))
        return invoices_to_print.filtered(lambda inv: inv.invoice_pdf_report_id)

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
        for aml in self.unreconciled_aml_ids.filtered('date_maturity'):
            eligible_levels = previous_levels.filtered(lambda level: (today - aml.date_maturity).days >= level.delay)
            if eligible_levels:
                aml.followup_line_id = max(eligible_levels, key=lambda level: level.delay)

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

    def _get_all_followup_data(self):
        if 'res_partner_all_followup' in self.env.cr.cache:
            return self.env.cr.cache['res_partner_all_followup']

        # Put the data in a cache in the cursor to avoid running costly query multiple times in same transaction.
        # Only do it if the table doesn't exist yet.
        query, params = self._get_followup_data_query()
        self.env.cr.execute(query, params)
        self.env.cr.cache['res_partner_all_followup'] = {
            r['partner_id']: r for r in self.env.cr.dictfetchall()
        }
        return self.env.cr.cache['res_partner_all_followup']

    def _query_followup_data(self, all_partners=False):
        if all_partners:
            return self._get_all_followup_data()
        if not self.ids:
            return {}
        if 'res_partner_all_followup' in self.env.cr.cache:
            cache_dict = self.env.cr.cache['res_partner_all_followup']
            return {id_: cache_dict[id_] for id_ in self.ids if id_ in cache_dict}
        query, params = self._get_followup_data_query(self.ids)
        self.env.cr.execute(query, params)
        return {r['partner_id']: r for r in self.env.cr.dictfetchall()}

    def _get_followup_data_query(self, partner_ids=None):
        self.env['account.move.line'].check_access('read')
        self.env['account.move.line'].flush_model()
        self.env['res.partner'].flush_model()
        self.env['account_followup.followup.line'].flush_model()
        ResPartner = self.env['res.partner']
        extra_join_conditions = self._get_followup_data_query_extra_join_conditions()
        return f"""
            SELECT partner.id as partner_id,
                   ful.id as followup_line_id,
                   CASE WHEN partner.amount_residual <= 0 THEN 'no_action_needed'
                        WHEN in_need_of_action_aml.id IS NOT NULL AND (followup_next_action_date IS NULL OR followup_next_action_date <= %(current_date)s) THEN 'in_need_of_action'
                        WHEN exceeded_unreconciled_aml.id IS NOT NULL THEN 'with_overdue_invoices'
                        ELSE 'no_action_needed' END as followup_status
            FROM (
          SELECT partner.id,
                 {self.env.cr.mogrify(ResPartner._field_to_sql('partner', 'followup_next_action_date')).decode(self.env.cr.connection.encoding)} AS followup_next_action_date,
                 MAX(COALESCE(next_ful.delay, ful.delay)) as followup_delay,
                 SUM(aml.amount_residual) as amount_residual
            FROM res_partner partner
            JOIN account_move_line aml ON aml.partner_id = partner.id
            JOIN account_account account ON account.id = aml.account_id
       LEFT JOIN account_followup_followup_line ful ON ful.id = aml.followup_line_id
       LEFT JOIN account_followup_followup_line next_ful ON next_ful.id = (
                    SELECT next_ful.id
                      FROM account_followup_followup_line next_ful
                     WHERE next_ful.delay > COALESCE(ful.delay, %(min_delay)s - 1)
                       AND next_ful.company_id = %(company_id)s
                  ORDER BY next_ful.delay ASC
                     LIMIT 1
                 )
           WHERE account.deprecated IS NOT TRUE
             AND account.account_type = 'asset_receivable'
             AND aml.parent_state = 'posted'
             AND aml.reconciled IS NOT TRUE
             AND aml.company_id = ANY(%(company_ids)s)
             {"" if partner_ids is None else "AND aml.partner_id IN %(partner_ids)s"}
        GROUP BY partner.id
            ) partner
            LEFT JOIN account_followup_followup_line ful ON ful.delay = partner.followup_delay AND ful.company_id = %(company_id)s
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
                   AND line.company_id = ANY(%(company_ids)s)
                   AND COALESCE(ful.delay, %(min_delay)s - 1) < partner.followup_delay
                   AND line.date_maturity IS NOT NULL
                   AND line.date_maturity + COALESCE(ful.delay, %(min_delay)s - 1) < %(current_date)s
                   {extra_join_conditions}
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
                   AND line.company_id = ANY(%(company_ids)s)
                   AND line.date_maturity IS NOT NULL
                   AND line.date_maturity < %(current_date)s
                   {extra_join_conditions}
                 LIMIT 1
            ) exceeded_unreconciled_aml ON true
        """, {
            'company_ids': self.env.company.search([('id', 'child_of', self.env.company.id)]).ids,
            'company_id': self.env.company.id,
            'partner_ids': tuple(partner_ids or []),
            'current_date': fields.Date.context_today(self),  # Allow mocking the current day for testing purpose.
            'min_delay': self._get_first_followup_level().delay or 0,
        }

    def _get_followup_data_query_extra_join_conditions(self):
        """ Hook method to add extra join conditions. """
        return ''

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

    def _get_followup_report(self, options):
        followup_report = (
                self.env.ref('account_reports.followup_report', raise_if_not_found=False)
                or self.env.ref('account_reports.customer_statement_report', raise_if_not_found=False)
                or self.env.ref('account_reports.partner_ledger_report')
        )
        options = followup_report.get_options({
            'forced_companies': self.env.company.search([('id', 'child_of', self.env.context.get('allowed_company_ids', self.env.company.id))]).ids,
            'partner_ids': self.ids,
            'unfold_all': True,
            'unreconciled': True,
            'all_entries': False,
            'export_mode': 'print',
        })
        return self._get_partner_account_report_attachment(followup_report, options=options).id

    def _get_followup_attachments(self, options):
        res_attachment_ids = options.get('attachment_ids', [])
        followup_line = options.get('followup_line')

        invoice_attachment_ids = self._get_invoices_to_print(options).invoice_pdf_report_id.ids
        if not options.get('join_invoices', followup_line.join_invoices):
            res_attachment_ids = []
        if options.get('manual_followup'):
            res_attachment_ids = [attachment for attachment in res_attachment_ids if attachment not in invoice_attachment_ids]

        # Add the Follow-up report
        options['report_attachment_id'] = self._get_followup_report(options)
        res_attachment_ids.append(options['report_attachment_id'])

        # Add the attachments from the template
        if template_id := options.get('template_id', followup_line.mail_template_id):
            template_attachments = template_id._generate_template_attachments(self.ids, {'attachment_ids', 'report_template_ids'})[self.id]
            res_attachment_ids += template_attachments['attachment_ids']

            attachments_to_create = []
            for dynamic_report in template_attachments['attachments']:
                attachments_to_create.append({
                    'name': dynamic_report[0],
                    'datas': dynamic_report[1],
                    'res_model': self._name,
                    'res_id': self.id,
                })
            dynamic_attachments = self.env['ir.attachment'].create(attachments_to_create)
            res_attachment_ids += dynamic_attachments.ids

        if options.get('join_invoices', followup_line.join_invoices):
            # Add the PDFs from overdue invoices
            res_attachment_ids += invoice_attachment_ids

        options['attachment_ids'] = res_attachment_ids

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
            options['followup_line'] = followup_line
            self._update_next_followup_action_date(followup_line)

            self._get_followup_attachments(options)

            self._send_followup(options)

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
        for partner in in_need_of_action_auto[:1000]:
            try:
                partner._execute_followup_partner()
            except UserError as e:
                # followup may raise exception due to configuration issues
                # i.e. partner missing email
                partner._message_log(body=e)
                _logger.warning(e, exc_info=True)

    def _cron_execute_followup(self):
        for company in self.env["res.company"].search([]):
            # Since the cache is done by database and not by company, we need to invalidate in this special case
            # where the context is changing in the same transaction
            self.env.cr.cache.pop('res_partner_all_followup', None)
            self.with_context(allowed_company_ids=company.ids)._cron_execute_followup_company()

    def _show_pay_now_button(self):
        invoice_online_payment = bool(self.env['ir.config_parameter'].sudo().get_param('account_payment.enable_portal_payment'))
        payment_method_available = bool(self.env['payment.method'].sudo().search_count([('active', '=', 'True')]))
        return invoice_online_payment and payment_method_available

    def _compute_has_moves(self):
        query = self.env['res.partner']._search([('id', 'in', self.ids)])
        account_move_query = self.env["account.move"]._search(
            [
                ("company_id", "in", self.env.companies.ids),
                "|",
                ("partner_id", "=", SQL.identifier(query.table, "id")),
                "|",
                ("partner_shipping_id", "=", SQL.identifier(query.table, "id")),
                ("commercial_partner_id", "=", SQL.identifier(query.table, "id")),
            ]
        )
        result = dict(self.env.execute_query(query.select(
            "id",
            SQL(
                "EXISTS (%s) AS has_moves",
                account_move_query.subselect(SQL.identifier(account_move_query.table, "id")),
            ),
        )))

        for partner in self:
            partner.has_moves = result.get(partner.id, False)

    def _get_followup_report_pdf(self, options):
        """
        Generate the follow-up report and return a tuple (filename, pdf_bin).
        """
        tz_date_str = format_date(self.env, fields.Date.today(), lang_code=self.env.user.lang or get_lang(self.env).code)
        # To avoid having dots in the name of the file.
        tz_date_str = tz_date_str.replace('.', '-')
        followup_letter_name = _("Follow-up %(partner)s - %(date)s.pdf", partner=self.display_name, date=tz_date_str)

        action = self.env.ref('account_followup.action_report_followup')
        followup_letter = action.with_context(lang=self.lang or self.env.user.lang)._render_qweb_pdf('account_followup.report_followup_print_all', self.id, data={'options': options or {}})[0]

        return followup_letter_name, followup_letter

    def _get_followup_report_attachment(self, options):
        """
        Generate the follow-up report and returns it as an attachment.
        """

        followup_letter_name, followup_letter = self._get_followup_report_pdf(options)
        return self.env['ir.attachment'].create({
            'name': followup_letter_name,
            'raw': followup_letter,
            'res_id': self.id,
            'res_model': 'res.partner',
            'type': 'binary',
            'mimetype': 'application/pdf',
        })
