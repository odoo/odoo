# -*- coding: utf-8 -*-
import ast

from odoo.addons.account.models.exceptions import TaxClosingNonPostedDependingMovesError
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_date
from odoo.tools import date_utils
from odoo.addons.web.controllers.utils import clean_action

from dateutil.relativedelta import relativedelta
from markupsafe import Markup


class AccountMove(models.Model):
    _inherit = "account.move"

    # used for VAT closing, containing the end date of the period this entry closes
    tax_closing_report_id = fields.Many2one(comodel_name='account.report')
    # technical field used to know whether to show the tax closing alert or not
    tax_closing_alert = fields.Boolean(compute='_compute_tax_closing_alert')

    def _post(self, soft=True):
        # Overridden to create carryover external values and join the pdf of the report when posting the tax closing
        for move in self.filtered(lambda m: m.tax_closing_report_id):
            report = move.tax_closing_report_id
            options = move._get_tax_closing_report_options(move.company_id, move.fiscal_position_id, report, move.date)
            move._close_tax_period(report, options)

        return super()._post(soft)

    def action_post(self):
        # In the case of a TaxClosingNonPostedDependingMovesError, which can occur when dealing with branches or tax
        # units during the closing process, the parent company may have non-posted closing entries from other companies.
        # If this exception occurs, we will return an action client that will display a component indicating that there
        # are non-posted dependent moves, along with a link to those moves.
        # Also, we are not using a RedirectWarning because it will force a rollback on the closing move created for
        # depending companies.
        try:
            res = super().action_post()
        except TaxClosingNonPostedDependingMovesError as exception:
            return {
                "type": "ir.actions.client",
                "tag": "account_reports.redirect_action",
                "target": "new",
                "name": "Depending Action",
                "params": {
                    "depending_action": exception.args[0],
                    "message": _("It seems there is some depending closing move to be posted"),
                    "button_text": _("Depending moves"),
                },
                'context': {
                    'dialog_size': 'medium',
                }
            }
        return res

    def button_draft(self):
        # Overridden in order to delete the carryover values when resetting the tax closing to draft
        super().button_draft()
        for closing_move in self.filtered(lambda m: m.tax_closing_report_id):
            report = closing_move.tax_closing_report_id
            options = closing_move._get_tax_closing_report_options(closing_move.company_id, closing_move.fiscal_position_id, report, closing_move.date)
            closing_months_delay = closing_move.company_id._get_tax_periodicity_months_delay(report)

            carryover_values = self.env['account.report.external.value'].search([
                ('carryover_origin_report_line_id', 'in', report.line_ids.ids),
                ('date', '=', options['date']['date_to']),
            ])

            carryover_impacted_period_end = fields.Date.from_string(options['date']['date_to']) + relativedelta(months=closing_months_delay)
            violated_lock_dates = closing_move.company_id._get_lock_date_violations(
                carryover_impacted_period_end, fiscalyear=False, sale=False, purchase=False, tax=True, hard=True,
            ) if carryover_values else None

            if violated_lock_dates:
                raise UserError(_("You cannot reset this closing entry to draft, as it would delete carryover values impacting the tax report of a locked period. "
                                  "Please change the following lock dates to proceed: %(lock_date_info)s.",
                                  lock_date_info=self.env['res.company']._format_lock_dates(violated_lock_dates)))

            if self._has_subsequent_posted_closing_moves():
                raise UserError(_("You cannot reset this closing entry to draft, as another closing entry has been posted at a later date."))

            carryover_values.unlink()

    def _has_subsequent_posted_closing_moves(self):
        self.ensure_one()
        closing_domains = [
            ('company_id', '=', self.company_id.id),
            ('tax_closing_report_id', '!=', False),
            ('state', '=', 'posted'),
            ('date', '>', self.date),
            ('fiscal_position_id', '=', self.fiscal_position_id.id)
        ]
        return bool(self.env['account.move'].search_count(closing_domains, limit=1))

    def _get_tax_to_pay_on_closing(self):
        self.ensure_one()
        tax_payable_accounts = self.env['account.tax.group'].search([
            ('company_id', '=', self.company_id.id),
        ]).tax_payable_account_id
        payable_lines = self.line_ids.filtered(lambda line: line.account_id in tax_payable_accounts)
        return self.currency_id.round(-sum(payable_lines.mapped('balance')))

    def _action_tax_to_pay_wizard(self):
        # hook for l10n tax payment wizard
        return self.action_open_tax_report()

    def _action_tax_to_send(self):
        return self.action_open_tax_report()

    def _action_tax_report_error(self):
        # hook for l10n tax report errors
        return self.action_open_tax_report()

    def action_open_tax_report(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account_reports.action_account_report_gt")
        if not self.tax_closing_report_id:
            raise UserError(_("You can't open a tax report from a move without a VAT closing date."))
        options = self._get_tax_closing_report_options(self.company_id, self.fiscal_position_id, self.tax_closing_report_id, self.date)
        # Pass options in context and set ignore_session: true to prevent using session options
        action.update({'params': {'options': options, 'ignore_session': True}})
        return action

    def _close_tax_period(self, report, options):
        """ Closes tax closing entries. The tax closing activities on them will be marked done, and the next tax closing entry
        will be generated or updated (if already existing). Also, a pdf of the tax report at the time of closing
        will be posted in the chatter of each move.

        The tax lock date of each  move's company will be set to the move's date in case no other draft tax closing
        move exists for that company (whatever their foreign VAT fiscal position) before or at that date, meaning that
        all the tax closings have been performed so far.
        """
        self.ensure_one()
        if not self.env.user.has_group('account.group_account_manager'):
            raise UserError(_('Only Billing Administrators are allowed to change lock dates!'))
        report = self.tax_closing_report_id
        options = self._get_tax_closing_report_options(self.company_id, self.fiscal_position_id, report, self.date)

        sender_company = report._get_sender_company_for_export(options)
        company_ids = report.get_report_company_ids(options)
        if sender_company == self.company_id:
            depending_closings = self.env['account.tax.report.handler']._get_tax_closing_entries_for_closed_period(report, options, self.env['res.company'].browse(company_ids), posted_only=False) - self
            depending_closings_to_post = depending_closings.filtered(lambda x: x.state == 'draft')
            if depending_closings_to_post:
                depending_action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
                depending_action = clean_action(depending_action, env=self.env)

                if len(depending_closings_to_post) == 1:
                    depending_action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
                    depending_action['res_id'] = depending_closings_to_post.id
                else:
                    depending_action['domain'] = [('id', 'in', depending_closings_to_post.ids)]
                    depending_action['context'] = dict(ast.literal_eval(depending_action['context']))
                    depending_action['context'].pop('search_default_posted', None)

                # In case of dependent moves, we will raise an error that will be caught in the action_post method.
                # When the exception is caught, a component will inform the user that there are some dependent moves
                # to be posted and provide a link to these moves.
                raise TaxClosingNonPostedDependingMovesError(depending_action)

            # Generate the carryover values.
            report.with_context(allowed_company_ids=company_ids)._generate_carryover_external_values(options)

            # Post the message with the attachments (PDF of the report, and possibly an additional export file)
            attachments = self._get_vat_report_attachments(report, options)
            subject = _(
                "Vat closing from %(date_from)s to %(date_to)s",
                date_from=format_date(self.env, options['date']['date_from']),
                date_to=format_date(self.env, options['date']['date_to']),
            )
            self.with_context(no_new_invoice=True).message_post(body=self.ref, subject=subject, attachments=attachments)

            # Log a note on depending closings, redirecting to the main one
            for closing_move in depending_closings:
                closing_move.message_post(body=_(
                    "The attachments of the tax report can be found on the %(link_start)sclosing entry%(link_end)s of the representative company.",
                    link_start=Markup('<a href="#" data-oe-model="account.move" data-oe-id="%s">') % self.id,
                    link_end=Markup("</a>"),
                ))

            # End activity
            activity = self.company_id._get_tax_closing_reminder_activity(report.id, self.date, self.fiscal_position_id.id)
            if activity:
                activity.action_done()

            # Generate next activity
            self.company_id._generate_tax_closing_reminder_activity(self.tax_closing_report_id, self.date + relativedelta(days=1), self.fiscal_position_id if self.fiscal_position_id.foreign_vat else None)

        if not self.fiscal_position_id and (not self.company_id.tax_lock_date or self.date > self.company_id.tax_lock_date):
            self.env['account.report']._generate_default_external_values(options['date']['date_from'], options['date']['date_to'], True)
            self.company_id.sudo().tax_lock_date = self.date

        self._close_tax_period_create_activities()

    def _get_tax_period_description(self):
        self.ensure_one()
        period_start, period_end = self.company_id._get_tax_closing_period_boundaries(self.date, self.tax_closing_report_id)
        return self.company_id._get_tax_closing_move_description(self.company_id._get_tax_periodicity(self.tax_closing_report_id), period_start, period_end, self.fiscal_position_id, self.tax_closing_report_id)

    def _close_tax_period_create_activities(self):
        mat_to_send_xml_id = 'account_reports.mail_activity_type_tax_report_to_be_sent'
        mat_to_send = self.env.ref(mat_to_send_xml_id, raise_if_not_found=False)
        if not mat_to_send:
            # As this is introduced in stable, we ensure data exists by creating them on the fly if needed
            mat_to_send = self.env['mail.activity.type'].sudo()._load_records([{
                'xml_id': mat_to_send_xml_id,
                'noupdate': False,
                'values': {
                    'name': 'Tax Report Ready',
                    'summary': 'Tax report is ready to be sent to the administration',
                    'category': 'tax_report',
                    'delay_count': '0',
                    'delay_unit': 'days',
                    'delay_from': 'current_date',
                    'res_model': 'account.move',
                    'chaining_type': 'suggest',
                }
            }])
        mat_to_pay_xml_id = 'account_reports.mail_activity_type_tax_report_to_pay'
        mat_to_pay = self.env.ref(mat_to_pay_xml_id, raise_if_not_found=False)

        act_user = mat_to_send.default_user_id
        if act_user and not (self.company_id in act_user.company_ids and act_user.has_group('account.group_account_manager')):
            act_user = self.env['res.users']

        moves_without_send_activity = self.filtered_domain([
            '|',
            ('activity_ids', '=', False),
            ('activity_ids', 'not any', [('activity_type_id.id', '=', mat_to_send.id)]),
        ])

        for move in moves_without_send_activity:
            period_desc = move._get_tax_period_description()
            move.with_context(mail_activity_quick_update=True).activity_schedule(
                act_type_xmlid=mat_to_send_xml_id,
                summary=_("Send tax report: %s", period_desc),
                date_deadline=fields.Date.context_today(move),
                user_id=act_user.id or self.env.user.id,
            )

            if mat_to_pay and mat_to_pay not in move.activity_ids.activity_type_id and move._get_tax_to_pay_on_closing() > 0:
                move.with_context(mail_activity_quick_update=True).activity_schedule(
                    act_type_xmlid=mat_to_pay_xml_id,
                    summary=_("Pay tax: %s", period_desc),
                    date_deadline=fields.Date.context_today(move),
                    user_id=act_user.id or self.env.user.id,
                )

    def refresh_tax_entry(self):
        for move in self.filtered(lambda m: m.tax_closing_report_id and m.state == 'draft'):
            report = move.tax_closing_report_id
            options = move._get_tax_closing_report_options(move.company_id, move.fiscal_position_id, report, move.date)
            self.env[report.custom_handler_model_name or 'account.generic.tax.report.handler']._generate_tax_closing_entries(report, options, closing_moves=move)

    @api.model
    def _get_tax_closing_report_options(self, company, fiscal_position, report, date_inside_period):
        _dummy, date_to = company._get_tax_closing_period_boundaries(date_inside_period, report)

        # In case the company submits its report in different regions, a closing entry
        # is made for each fiscal position defining a foreign VAT.
        # We hence need to make sure to select a tax report in the right country when opening
        # the report (in case there are many, we pick the first one available; it doesn't impact the closing)
        if fiscal_position and fiscal_position.foreign_vat:
            fpos_option = fiscal_position.id
            report_country = fiscal_position.country_id
        else:
            fpos_option = 'domestic'
            report_country = company.account_fiscal_country_id

        options = {
            'date': {
                'date_to': fields.Date.to_string(date_to),
                'filter': 'custom_tax_period',
                'mode': 'range',
            },
            'selected_variant_id': report.id,
            'sections_source_id': report.id,
            'fiscal_position': fpos_option,
            'tax_unit': 'company_only',
        }

        if report.filter_multi_company == 'tax_units':
            # Enforce multicompany if the closing is done for a tax unit
            candidate_tax_unit = company.account_tax_unit_ids.filtered(lambda x: x.country_id == report_country)
            if candidate_tax_unit:
                options['tax_unit'] = candidate_tax_unit.id
                company_ids = candidate_tax_unit.company_ids.ids
            else:
                same_vat_branches = self.env.company._get_branches_with_same_vat()
                # Consider the one with the least number of parents (highest in hierarchy) as the active company, coming first
                company_ids = same_vat_branches.sorted(lambda x: len(x.parent_ids)).ids
        else:
            company_ids = self.env.company.ids

        return report.with_context(allowed_company_ids=company_ids).get_options(previous_options=options)

    def _get_vat_report_attachments(self, report, options):
        # Fetch pdf
        pdf_data = report.export_to_pdf(options)
        return [(pdf_data['file_name'], pdf_data['file_content'])]

    def _compute_tax_closing_alert(self):
        for move in self:
            move.tax_closing_alert = (
                move.state == 'posted'
                and move.tax_closing_report_id
                and move.company_id.tax_lock_date
                and move.company_id.tax_lock_date < move.date
            )
