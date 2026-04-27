# -*- coding: utf-8 -*-

import logging
import requests
from dateutil.relativedelta import relativedelta
from requests.exceptions import RequestException, Timeout

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def __get_bank_statements_available_sources(self):
        rslt = super(AccountJournal, self).__get_bank_statements_available_sources()
        rslt.append(("online_sync", _("Online Synchronization")))
        return rslt

    next_link_synchronization = fields.Datetime("Online Link Next synchronization", related='account_online_link_id.next_refresh')
    expiring_synchronization_date = fields.Date(related='account_online_link_id.expiring_synchronization_date')
    expiring_synchronization_due_day = fields.Integer(compute='_compute_expiring_synchronization_due_day')
    account_online_account_id = fields.Many2one('account.online.account', copy=False, ondelete='set null')
    account_online_link_id = fields.Many2one('account.online.link', related='account_online_account_id.account_online_link_id', readonly=True, store=True)
    account_online_link_state = fields.Selection(related="account_online_link_id.state", readonly=True)
    renewal_contact_email = fields.Char(
        string='Connection Requests',
        help='Comma separated list of email addresses to send consent renewal notifications 15, 3 and 1 days before expiry',
        default=lambda self: self.env.user.email,
    )
    online_sync_fetching_status = fields.Selection(related="account_online_account_id.fetching_status", readonly=True)

    def write(self, vals):
        # When changing the bank_statement_source, unlink the connection if there is any
        if 'bank_statements_source' in vals and vals.get('bank_statements_source') != 'online_sync':
            for journal in self:
                if journal.bank_statements_source == 'online_sync':
                    # unlink current connection
                    vals['account_online_account_id'] = False
                    journal.account_online_link_id.has_unlinked_accounts = True
        return super().write(vals)

    @api.depends('expiring_synchronization_date')
    def _compute_expiring_synchronization_due_day(self):
        for record in self:
            if record.expiring_synchronization_date:
                due_day_delta = record.expiring_synchronization_date - fields.Date.context_today(record)
                record.expiring_synchronization_due_day = due_day_delta.days
            else:
                record.expiring_synchronization_due_day = 0

    def _fill_bank_cash_dashboard_data(self, dashboard_data):
        super()._fill_bank_cash_dashboard_data(dashboard_data)
        # Caching data to avoid one call per journal
        self.browse(list(dashboard_data.keys())).fetch(['type', 'account_online_account_id'])
        for journal_id, journal_data in dashboard_data.items():
            journal = self.browse(journal_id)
            journal_data['display_connect_bank_in_dashboard'] = journal.type in ('bank', 'credit') \
                                                                and not journal.account_online_account_id \
                                                                and journal.company_id.id == self.env.company.id

    @api.constrains('account_online_account_id')
    def _check_account_online_account_id(self):
        for journal in self:
            if len(journal.account_online_account_id.journal_ids) > 1:
                raise ValidationError(_('You cannot have two journals associated with the same Online Account.'))

    def _fetch_online_transactions(self):
        for journal in self:
            try:
                journal.account_online_link_id._pop_connection_state_details(journal=journal)
                journal.manual_sync()
                # for cron jobs it is usually recommended committing after each iteration,
                # so that a later error or job timeout doesn't discard previous work
                self.env.cr.commit()
            except (UserError, RedirectWarning):
                # We need to rollback here otherwise the next iteration will still have the error when trying to commit
                self.env.cr.rollback()

    def fetch_online_sync_favorite_institutions(self):
        self.ensure_one()
        timeout = int(self.env['ir.config_parameter'].sudo().get_param('account_online_synchronization.request_timeout')) or 60
        endpoint_url = self.env['account.online.link']._get_odoofin_url('/proxy/v1/get_dashboard_institutions')
        params = {'country': self.sudo().company_id.account_fiscal_country_id.code, 'limit': 28}
        try:
            resp = requests.post(endpoint_url, json=params, timeout=timeout)
            resp_dict = resp.json()['result']
            for institution in resp_dict:
                if institution['picture'].startswith('/'):
                    institution['picture'] = self.env['account.online.link']._get_odoofin_url(institution['picture'])
            return resp_dict
        except (Timeout, ConnectionError, RequestException, ValueError) as e:
            _logger.warning(e)
            return []

    @api.model
    def _cron_fetch_waiting_online_transactions(self):
        """ This method is only called when the user fetch transactions asynchronously.
            We only fetch transactions on synchronizations that are in "waiting" status.
            Once the synchronization is done, the status is changed for "done".
            We have to that to avoid having too much logic in the same cron function to do
            2 different things. This cron should only be used for asynchronous fetchs.
        """

        # 'limit_time_real_cron' and 'limit_time_real' default respectively to -1 and 120.
        # Manual fallbacks applied for non-POSIX systems where this key is disabled (set to None).
        limit_time = tools.config['limit_time_real_cron'] or -1
        if limit_time <= 0:
            limit_time = tools.config['limit_time_real'] or 120
        journals = self.search([
            '|',
                ('online_sync_fetching_status', 'in', ('planned', 'waiting')),
                '&',
                    ('online_sync_fetching_status', '=', 'processing'),
                    ('account_online_link_id.last_refresh', '<', fields.Datetime.now() - relativedelta(seconds=limit_time)),
        ])
        journals.with_context(cron=True)._fetch_online_transactions()

    @api.model
    def _cron_fetch_online_transactions(self):
        """ This method is called by the cron (by default twice a day) to fetch (for all journals)
            the new transactions.
        """
        journals = self.search([('account_online_account_id', '!=', False)])
        journals.with_context(cron=True)._fetch_online_transactions()

    @api.model
    def _cron_send_reminder_email(self):
        for journal in self.search([('account_online_account_id', '!=', False)]):
            if journal.expiring_synchronization_due_day in {1, 3, 15}:
                journal.action_send_reminder()

    def manual_sync(self):
        self.ensure_one()
        if self.account_online_link_id:
            account = self.account_online_account_id
            return self.account_online_link_id._fetch_transactions(accounts=account)

    def unlink(self):
        """
        Override of the unlink method.
        That's useful to unlink account.online.account too.
        """
        if self.account_online_account_id:
            self.account_online_account_id.unlink()
        return super(AccountJournal, self).unlink()

    def action_configure_bank_journal(self):
        """
        Override the "action_configure_bank_journal" and change the flow for the
        "Configure" button in dashboard.
        """
        self.ensure_one()
        return self.env['account.online.link'].action_new_synchronization()

    def action_open_account_online_link(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.account_online_link_id.name,
            'res_model': 'account.online.link',
            'target': 'main',
            'view_mode': 'form',
            'views': [[False, 'form']],
            'res_id': self.account_online_link_id.id,
        }

    def action_extend_consent(self):
        """
        Extend the consent of the user by redirecting him to update his credentials
        """
        self.ensure_one()
        return self.account_online_link_id._open_iframe(
            mode='updateCredentials',
            include_param={
                'account_online_identifier': self.account_online_account_id.online_identifier,
            },
        )

    def action_reconnect_online_account(self):
        self.ensure_one()
        return self.account_online_link_id.action_reconnect_account()

    def action_send_reminder(self):
        self.ensure_one()
        self._portal_ensure_token()
        template = self.env.ref('account_online_synchronization.email_template_sync_reminder')
        subtype = self.env.ref('account_online_synchronization.bank_sync_consent_renewal')
        self.message_post_with_source(source_ref=template, subtype_id=subtype.id)

    def action_open_missing_transaction_wizard(self):
        """ This method allows to open the wizard to fetch the missing
            transactions and the pending ones.
            Depending on where the function is called, we'll receive
            one journal or none of them.
            If we receive more or less than one journal, we do not set
            it on the wizard, the user should select it by himself.

            :return: An action opening the wizard.
        """
        journal_id = None
        if len(self) == 1:
            if not self.account_online_account_id or self.account_online_link_state != 'connected':
                raise UserError(_("You can't find missing transactions for a journal that isn't connected."))

            journal_id = self.id

        wizard = self.env['account.missing.transaction.wizard'].create({'journal_id': journal_id})
        return {
            'name': _("Find Missing Transactions"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.missing.transaction.wizard',
            'res_id': wizard.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    def action_open_duplicate_transaction_wizard(self, from_date=None):
        """ This method allows to open the wizard to find duplicate transactions.
            :param from_date: date from with we must check for duplicates.

            :return: An action opening the wizard.
        """
        wizard = self.env['account.duplicate.transaction.wizard'].create({
            'journal_id': self.id if len(self) == 1 else None,
            **({'date': from_date} if from_date else {}),
        })
        return wizard._get_records_action(name=_("Find Duplicate Transactions"))

    def _has_duplicate_transactions(self, date_from):
        """ Has any transaction with
               - same amount &
               - same date &
               - same account number
            We do not check on online_transaction_identifier because this is called after the fetch
            where transitions would already have been filtered on existing online_transaction_identifier.

            :param from_date: date from with we must check for duplicates.
        """
        self.env.cr.execute(SQL.join(SQL(''), [
            self._get_duplicate_amount_date_account_transactions_query(date_from),
            SQL('LIMIT 1'),
        ]))
        return bool(self.env.cr.rowcount)

    def _get_duplicate_transactions(self, date_from):
        """Find all transaction with
               - same amount &
               - same date &
               - same account number
               or
               - same transaction id

            :param from_date: date from with we must check for duplicates.
        """
        query = SQL.join(SQL(''), [
            self._get_duplicate_amount_date_account_transactions_query(date_from),
            SQL('UNION'),
            self._get_duplicate_online_transaction_identifier_transactions_query(date_from),
            SQL('ORDER BY ids'),
        ])
        return [res[0] for res in self.env.execute_query(query)]

    def _get_duplicate_amount_date_account_transactions_query(self, date_from):
        self.ensure_one()
        return SQL('''
              SELECT ARRAY_AGG(st_line.id ORDER BY st_line.id) AS ids
                FROM account_bank_statement_line st_line
                JOIN account_move move ON move.id = st_line.move_id
               WHERE st_line.journal_id = %(journal_id)s AND move.date >= %(date_from)s
            GROUP BY st_line.currency_id, st_line.amount, st_line.account_number, move.date
              HAVING count(st_line.id) > 1
            ''',
            journal_id=self.id,
            date_from=date_from,
        )

    def _get_duplicate_online_transaction_identifier_transactions_query(self, date_from):
        return SQL('''
              SELECT ARRAY_AGG(st_line.id ORDER BY st_line.id) AS ids
                FROM account_bank_statement_line st_line
                JOIN account_move move ON move.id = st_line.move_id
               WHERE st_line.journal_id = %(journal_id)s AND
                     move.date >= %(prior_date)s AND
                     st_line.online_transaction_identifier IS NOT NULL
            GROUP BY st_line.online_transaction_identifier
              HAVING count(st_line.id) > 1 AND BOOL_OR(move.date >= %(date_from)s)  -- at least one date is > date_from
                ''',
                journal_id=self.id,
                date_from=date_from,
                prior_date=date_from - relativedelta(months=3),  # allow 1 of duplicate statements to be older than "from" date
            )

    def action_open_dashboard_asynchronous_action(self):
        """ This method allows to open action asynchronously
            during the fetching process.
            When a user clicks on the Fetch Transactions button in
            the dashboard, we fetch the transactions asynchronously
            and save connection state details on the synchronization.
            This action allows the user to open the action saved in
            the connection state details.
        """
        self.ensure_one()

        if not self.account_online_account_id:
            raise UserError(_("You can only execute this action for bank-synchronized journals."))

        connection_state_details = self.account_online_link_id._pop_connection_state_details(journal=self)
        if connection_state_details and connection_state_details.get('action'):
            if connection_state_details.get('error_type') == 'redirect_warning':
                self.env.cr.commit()
                raise RedirectWarning(connection_state_details['error_message'], connection_state_details['action'], _('Report Issue'))
            else:
                return connection_state_details['action']

        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}

    def _get_journal_dashboard_data_batched(self):
        dashboard_data = super()._get_journal_dashboard_data_batched()
        for journal in self.filtered(lambda j: j.type in ('bank', 'credit')):
            if journal.account_online_account_id:
                if journal.company_id.id not in self.env.companies.ids:
                    continue
                connection_state_details = journal.account_online_link_id._get_connection_state_details(journal=journal)
                if not connection_state_details and journal.account_online_account_id.fetching_status in ('waiting', 'processing'):
                    connection_state_details = {'status': 'fetching'}
                dashboard_data[journal.id]['connection_state_details'] = connection_state_details
                dashboard_data[journal.id]['show_sync_actions'] = journal.account_online_link_id.show_sync_actions
        return dashboard_data

    def get_related_connection_state_details(self):
        """ This method allows JS widget to get the last connection state details
            It's useful if the user wasn't on the dashboard when we send the message
            by websocket that the asynchronous flow is finished.
            In case we don't have a connection state details and if the fetching
            status is set on "waiting" or "processing". We're returning that the sync
            is currently fetching.
        """
        self.ensure_one()
        connection_state_details = self.account_online_link_id._get_connection_state_details(journal=self)
        if not connection_state_details and self.account_online_account_id.fetching_status in ('waiting', 'processing'):
            connection_state_details = {'status': 'fetching'}
        return connection_state_details

    def _consume_connection_state_details(self):
        self.ensure_one()
        if self.account_online_link_id and self.env.user.has_group('account.group_account_manager'):
            # In case we have a bank synchronization connected to the journal
            # we want to remove the last connection state because it means that we
            # have "mark as read" this state, and we don't want to display it again to
            # the user.
            self.account_online_link_id._pop_connection_state_details(journal=self)

    def open_action(self):
        # Extends 'account_accountant'
        if not self._context.get('action_name') and self.type == 'bank' and self.bank_statements_source == 'online_sync':
            self._consume_connection_state_details()
            return self.env['account.bank.statement.line']._action_open_bank_reconciliation_widget(
                default_context={'search_default_journal_id': self.id},
            )
        return super().open_action()

    def action_open_reconcile(self):
        # Extends 'account_accountant'
        self._consume_connection_state_details()
        return super().action_open_reconcile()

    def action_open_bank_transactions(self):
        # Extends 'account_accountant'
        self._consume_connection_state_details()
        return super().action_open_bank_transactions()

    @api.model
    def _toggle_asynchronous_fetching_cron(self):
        cron = self.env.ref('account_online_synchronization.online_sync_cron_waiting_synchronization', raise_if_not_found=False)
        if cron:
            cron.sudo().toggle(model=self._name, domain=[('account_online_account_id', '!=', False)])
