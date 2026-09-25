# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import date_utils
from odoo.tools.misc import format_date

# MyInvois keeps two years of history.
SYNC_MONTH_COUNT = 24


class MyInvoisDocumentSyncWizard(models.TransientModel):
    _name = 'myinvois.document.sync.wizard'
    _description = 'Sync Received Documents Wizard'
    _check_company_auto = True

    @api.model
    def _default_journal_id(self):
        return self.env.company.l10n_my_edi_default_import_journal_id or self.env['account.journal'].search([
            *self.env['account.journal']._check_company_domain(self.env.company),
            ('type', '=', 'purchase'),
        ], limit=1)

    # ------------------
    # Fields declaration
    # ------------------

    company_id = fields.Many2one(
        comodel_name='res.company',
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    month = fields.Selection(
        selection='_selection_month',
        string='Month',
        help='The documents issued during this month will be synced.',
        required=True,
        default=lambda self: self._selection_month()[0][0],
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        help='The journal of the bills created from the received documents.',
        domain="[('type', '=', 'purchase')]",
        required=True,
        check_company=True,
        default=lambda self: self._default_journal_id(),
    )

    # -----------------
    # Selection methods
    # -----------------

    @api.model
    def _selection_month(self):
        """ The current month and the ones before it, as far back as MyInvois keeps documents. """
        current_month = date_utils.start_of(fields.Date.context_today(self), 'month')
        months = [current_month - relativedelta(months=index) for index in range(SYNC_MONTH_COUNT)]
        return [(fields.Date.to_string(month), format_date(self.env, month, date_format='MMM yyyy')) for month in months]

    # --------------
    # Action methods
    # --------------

    def button_sync(self):
        """ Create a draft bill for each new document received during the selected month. """
        self.ensure_one()
        proxy_user = self.company_id.sudo().l10n_my_edi_proxy_user_id
        if not proxy_user:
            raise UserError(self.env._("Please register for the E-Invoicing service in the settings first."))

        # A month always fits in the 31 days window of a single search.
        date_from = datetime.datetime.combine(fields.Date.to_date(self.month), datetime.time.min, tzinfo=ZoneInfo('Asia/Kuala_Lumpur'))
        date_to = min(
            date_from + relativedelta(months=1, seconds=-1),
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
                    'message': self.env._("No new document was received on MyInvois for %(month)s.", month=dict(self._selection_month())[self.month]),
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }

        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        action.update({
            'name': self.env._("Received Bills"),
            'domain': [('id', 'in', bills.ids)],
        })
        return action
