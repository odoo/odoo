# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
from datetime import timedelta
from itertools import islice

from lxml import etree

from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.addons.l10n_hu_edi.models.l10n_hu_edi_connection import L10nHuEdiConnection, L10nHuEdiConnectionError, XML_NAMESPACES


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_hu_group_vat = fields.Char(
        related='partner_id.l10n_hu_group_vat',
        readonly=False,
    )
    l10n_hu_tax_regime = fields.Selection(
        selection=[
            ('ie', 'Individual Exemption'),
            ('ca', 'Cash Accounting'),
            ('sb', 'Small Business'),
        ],
        string='NAV Tax Regime',
    )
    l10n_hu_edi_server_mode = fields.Selection(
        selection=[
            ('production', 'Production'),
            ('test', 'Test'),
            ('demo', 'Demo'),
        ],
        string='Server Mode',
        help="""
            - Production: Sends invoices to the NAV's production system.
            - Test: Sends invoices to the NAV's test system.
            - Demo: Mocks the NAV system (does not require credentials).
        """
    )
    l10n_hu_edi_username = fields.Char(
        string='NAV Username',
        groups='base.group_system',
    )
    l10n_hu_edi_password = fields.Char(
        string='NAV Password',
        groups='base.group_system',
    )
    l10n_hu_edi_signature_key = fields.Char(
        string='NAV Signature Key',
        groups='base.group_system',
    )
    l10n_hu_edi_replacement_key = fields.Char(
        string='NAV Replacement Key',
        groups='base.group_system',
    )
    l10n_hu_edi_last_transaction_recovery = fields.Datetime(
        string='Last transaction recovery (in production mode)',
        default=lambda self: fields.Datetime.now(),
    )

    def _l10n_hu_edi_configure_company(self):
        """ Single-time configuration for companies, to be applied when l10n_hu_edi is installed
        or a new company is created.
        """
        for company in self:
            # Set profit/loss accounts on cash rounding method
            profit_account = self.env['account.chart.template'].with_company(company).ref('l10n_hu_969', raise_if_not_found=False)
            loss_account = self.env['account.chart.template'].with_company(company).ref('l10n_hu_869', raise_if_not_found=False)
            rounding_method = self.env.ref('l10n_hu_edi.cash_rounding_1_huf', raise_if_not_found=False)
            if profit_account and loss_account and rounding_method:
                rounding_method.with_company(company).write({
                    'profit_account_id': profit_account.id,
                    'loss_account_id': loss_account.id,
                })

            # Activate cash rounding on the company
            res_config_id = self.env['res.config.settings'].create({
                'company_id': company.id,
                'group_cash_rounding': True,
            })
            res_config_id.execute()

    def _l10n_hu_edi_get_credentials_dict(self):
        self.ensure_one()
        credentials_dict = {
            'vat': self.vat,
            'mode': self.l10n_hu_edi_server_mode,
            'username': self.l10n_hu_edi_username,
            'password': self.l10n_hu_edi_password,
            'signature_key': self.l10n_hu_edi_signature_key,
            'replacement_key': self.l10n_hu_edi_replacement_key,
        }
        if self.l10n_hu_edi_server_mode != 'demo' and not all(credentials_dict.values()):
            raise UserError(_('Missing NAV credentials for company %s', self.name))
        return credentials_dict

    def _l10n_hu_edi_test_credentials(self):
        with L10nHuEdiConnection(self.env) as connection:
            for company in self:
                if not company.vat:
                    raise UserError(_('NAV Credentials: Please set the hungarian vat number on the company first!'))
                try:
                    connection.do_token_exchange(company._l10n_hu_edi_get_credentials_dict())
                except L10nHuEdiConnectionError as e:
                    raise UserError(
                        _('Incorrect NAV Credentials! Check that your company VAT number is set correctly. \nError details: %s', e)
                    ) from e

    def _l10n_hu_edi_recover_transactions(self, connection):
        """ Recover transactions that are in force but for some reason are not matched to the company's
        invoices, and update the invoice state correspondingly.

        This can happen, for example, if the invoice sending timed out: in that case, we don't have a
        transaction ID for the invoice. It can also happen if for some reason the transaction ID was
        overwritten by a new request, but the new request fails with a 'duplicate invoice' error.

        To do this, we request a list of all transactions made since l10n_hu_edi_last_transaction_recovery,
        and then we query the last 10 transactions whose transaction IDs are unknown by Odoo. We try to
        match them to invoices in Odoo, and if successful, update the invoice state.
        """

        for company in self:
            # We use the l10n_hu_edi_last_transaction_recovery time only in production mode
            # to indicate which transactions to request.
            # In test mode (where we expect far fewer invoices), we just take the last 24 hours.
            recovery_end_time = fields.Datetime.now()
            if company.l10n_hu_edi_server_mode == 'production':
                recovery_start_time = company.l10n_hu_edi_last_transaction_recovery
            else:
                recovery_start_time = recovery_end_time - timedelta(hours=24)

            # Old invoices are already up-to-date - no need to re-check them.
            invoices_to_check = self.env['account.move'].search([
                ('company_id', '=', company.id),
                ('l10n_hu_edi_send_time', '>=', recovery_start_time),
                ('l10n_hu_edi_state', '!=', False),
            ])
            # Step 1: Request a list of all transactions made during the specified time interval.
            page = 1
            available_pages = 1
            transactions = []
            while page <= available_pages:
                try:
                    transaction_list = connection.do_query_transaction_list(
                        company.sudo()._l10n_hu_edi_get_credentials_dict(),
                        recovery_start_time,
                        recovery_end_time,
                        page,
                    )
                except L10nHuEdiConnectionError as e:
                    return {
                        'error_title': _('Error listing transactions while attempting transaction recovery.'),
                        'errors': e.errors,
                    }

                available_pages = transaction_list['available_pages']
                transactions += transaction_list['transactions']
                page += 1

            # Step 2: Query unknown transactions in reverse order (latest first) and update invoice states accordingly.
            # If there are too many, we should only query the last 10, to avoid pointlessly making huge numbers of requests.
            transactions_to_query = (
                t for t in reversed(transactions)
                if t['username'] == company.sudo().l10n_hu_edi_username
                    and t['source'] == 'MGM'
                    and t['transaction_code'] not in invoices_to_check.mapped('l10n_hu_edi_transaction_code')
            )

            for transaction in islice(transactions_to_query, 10):
                try:
                    results = connection.do_query_transaction_status(
                        company.sudo()._l10n_hu_edi_get_credentials_dict(),
                        transaction['transaction_code'],
                        return_original_request=True,
                    )
                except L10nHuEdiConnectionError as e:
                    return {
                        'error_title': _('Error querying transaction while attempting transaction recovery.'),
                        'errors': e.errors,
                    }

                for processing_result in results['processing_results']:
                    invoice_name = processing_result['original_xml'].findtext('data:invoiceNumber', namespaces=XML_NAMESPACES)
                    canonicalized_attachment = etree.canonicalize(processing_result['original_file'])
                    annulment_invoice_name = processing_result['original_xml'].findtext('data:annulmentReference', namespaces=XML_NAMESPACES)

                    matched_invoice = invoices_to_check.filtered(
                        lambda m: (
                            # 1. Match invoice if the entire XML matches.
                            # For performance, we first check the invoice name before trying to match the whole XML.
                            (
                                m.name == invoice_name
                                and etree.canonicalize(base64.b64decode(m.l10n_hu_edi_attachment).decode())
                                    == canonicalized_attachment
                            )
                            or m.name == annulment_invoice_name
                        ) and (
                            # 2. We update the invoice state only if:
                            # - the invoice doesn't have a transaction code, or
                            # - it currently has a duplicate error, or
                            # - the current transaction is more recent than the latest transaction on the invoice
                            #   and is not a duplicate error (this avoid overwriting the state with a previous, obsolete one).
                            not m.l10n_hu_edi_transaction_code
                            or any(
                                'INVOICE_NUMBER_NOT_UNIQUE' in error or 'ANNULMENT_IN_PROGRESS' in error
                                for error in m.l10n_hu_edi_messages['errors']
                            )
                            or (
                                transaction['send_time'] >= m.l10n_hu_edi_send_time
                                and not (
                                    processing_result['technical_validation_messages']
                                    or any(
                                        message['validation_error_code'] in ['INVOICE_NUMBER_NOT_UNIQUE', 'ANNULMENT_IN_PROGRESS']
                                        for message in processing_result['business_validation_messages']
                                    )
                                )
                            )
                        )
                    )

                    if matched_invoice:
                        # Set the correct transaction code on the matched invoice
                        matched_invoice.l10n_hu_edi_transaction_code = transaction['transaction_code']
                        matched_invoice._l10n_hu_edi_process_query_transaction_result(processing_result, results['annulment_status'])

            # The server might still be processing transactions from the last 6 minutes,
            # so we should keep open the possibility of re-querying them.
            recovery_close_time = recovery_end_time - timedelta(minutes=6)
            if company.l10n_hu_edi_server_mode == 'production':
                company.l10n_hu_edi_last_transaction_recovery = recovery_close_time

            # Any invoices still in a 'timeout' state that are more than 6 minutes old and could not be matched should be considered not received.
            invoices_to_check.filtered(
                lambda m: m.l10n_hu_edi_state == 'send_timeout' and m.l10n_hu_edi_send_time < recovery_close_time
            ).write({
                'l10n_hu_invoice_chain_index': 0,
                'l10n_hu_edi_state': 'rejected',
            })

            invoices_to_check.filtered(
                lambda m: m.l10n_hu_edi_state == 'cancel_timeout' and m.l10n_hu_edi_send_time < recovery_close_time
            ).write({
                'l10n_hu_edi_state': 'confirmed_warning',
            })
