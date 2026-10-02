# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import date_utils
from odoo.tools.misc import format_date

SYNC_MONTH_COUNT = 24


class MyInvoisDocumentSyncWizard(models.TransientModel):
    _name = 'myinvois.document.sync.wizard'
    _description = 'Sync Received Documents Wizard'

    @api.model
    def _default_journal_id(self):
        return self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self.env.company),
            ('type', '=', 'purchase'),
        ], limit=1)

    # ------------------
    # Fields declaration
    # ------------------

    month = fields.Selection(
        selection='_selection_month',
        string='Month',
        help='The documents issued during this month will be synced.',
        required=True,
        default=lambda self: self._selection_month()[0][0],
    )
    date_from = fields.Date(string='From', compute='_compute_dates', store=True, readonly=False, required=True, precompute=True)
    date_to = fields.Date(string='To', compute='_compute_dates', store=True, readonly=False, required=True, precompute=True)
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        help='The journal of the bills created from the received documents. '
             'The documents received by the company of this journal are synced.',
        domain="[('type', '=', 'purchase')]",
        required=True,
        default=lambda self: self._default_journal_id(),
    )

    # -----------------
    # Selection methods
    # -----------------

    @api.model
    def _selection_month(self):
        """ The current month and the ones before it, as far back as MyInvois keeps documents. """
        current_month = date_utils.start_of(fields.Date.context_today(self.with_context(tz='Asia/Kuala_Lumpur')), 'month')
        months = [current_month - relativedelta(months=index) for index in range(SYNC_MONTH_COUNT)]
        return [(fields.Date.to_string(month), format_date(self.env, month, date_format='MMM yyyy')) for month in months]

    @api.depends('month')
    def _compute_dates(self):
        today = fields.Date.context_today(self.with_context(tz='Asia/Kuala_Lumpur'))
        for wizard in self:
            start = fields.Date.to_date(wizard.month)
            wizard.date_from = start
            wizard.date_to = min(start + relativedelta(months=1, days=-1), today) if start else False

    # --------------
    # Action methods
    # --------------

    def button_sync(self):
        """ Create a draft bill for each new document issued between the selected dates. """
        self.ensure_one()
        # The journal can be set through RPC: it must be one the user has access to.
        self.journal_id.check_access('read')
        proxy_user = self.journal_id.company_id.sudo().l10n_my_edi_proxy_user_id
        if not proxy_user:
            raise UserError(self.env._("Please register for the E-Invoicing service in the settings first."))

        month_start = fields.Date.to_date(self.month)
        month_end = month_start + relativedelta(months=1, days=-1)
        today = fields.Date.context_today(self.with_context(tz='Asia/Kuala_Lumpur'))
        if not self.date_from or not self.date_to or not month_start <= self.date_from <= self.date_to <= min(month_end, today):
            raise UserError(self.env._("Please choose a date range within the selected month, ending no later than today."))
        date_from = datetime.datetime.combine(self.date_from, datetime.time.min, tzinfo=ZoneInfo('Asia/Kuala_Lumpur'))
        date_to = min(
            datetime.datetime.combine(self.date_to, datetime.time(23, 59, 59), tzinfo=ZoneInfo('Asia/Kuala_Lumpur')),
            datetime.datetime.now(datetime.timezone.utc),
        )
        documents = self.env['myinvois.document']
        documents_data = documents._myinvois_fetch_received_documents(proxy_user, date_from, date_to)
        bills = documents._myinvois_import_received_documents(documents_data, self.journal_id)
        if not bills:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'info',
                    'message': self.env._("No new document was received on MyInvois for the selected dates."),
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }

        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        action.update({
            'name': self.env._("Received Bills"),
            'domain': [('id', 'in', bills.ids)],
        })
        return action
