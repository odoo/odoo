import json
import logging
import requests

from datetime import datetime
from zoneinfo import ZoneInfo

from odoo import api, fields, models
from odoo.tools import SQL
from odoo.tools.urls import urljoin


_logger = logging.getLogger(__name__)


class BankAccountVerification(models.Model):
    _name = 'l10n_pl.bank.account.verification'
    _description = 'PL Bank Account Verification'

    verification_status = fields.Selection(
        selection=[
            ('valid', 'Valid'),
            ('invalid', 'Invalid'),  # Bank account not referenced (in gov files) for partner's vat number
            ('incomplete_partner', 'Incomplete partner'),  # Inside Odoo, no API call
            ('not_found_partner', 'Partner not found'),  # API called, but cannot find the VAT number
            ('error', 'An error occurred during check with Government API'),  # API called -> error
        ],
        string="Verification Status",
        readonly=True,
        required=True,
        help="Flag the payment verification status with one of the following:\n"
            "- Valid: The partner VAT is linked to the bank account used for this payment.\n"
            "- Invalid: The partner VAT is not linked to the bank account used for this payment.\n"
            "- Incomplete partner: The partner has no VAT or no bank account.\n"
            "- Partner not found: Partner VAT not found in Government files.\n"
            "- Error: An error occurred during check with Government API.\n"
    )
    # Timestamp received by the API, in PL tz
    verification_timestamp = fields.Datetime("Verification Timestamp", readonly=True)
    # Technical field to ease search
    verification_date = fields.Date(
        compute='_compute_verification_date',
        store=True,
        index=False,
    )
    verification_request_id = fields.Char("Correlation ID", readonly=True)
    partner_bank_id = fields.Many2one('res.partner.bank', readonly=True, string="Bank Account")
    # We need to store the bank account number itself to prevent changes on the res.partner.bank record
    partner_bank_account_number = fields.Char(
        compute='_compute_partner_bank_account_number',
        readonly=True,
        store=True,
        index=False,
    )
    partner_id = fields.Many2one('res.partner', readonly=True, string="Partner")
    # We need to store the partner VAT itself to prevent changes on the res.partner record
    partner_vat = fields.Char(
        compute='_compute_partner_vat',
        readonly=True,
        store=True,
        index=False,
    )

    _verification_index = models.UniqueIndex("(verification_date, partner_bank_account_number, partner_vat)")

    @api.autovacuum
    def _gc_bank_account_verification(self):
        self.env.cr.execute("""
            SELECT tc.table_name,
                   kcu.column_name
              FROM information_schema.table_constraints AS tc
              JOIN information_schema.key_column_usage AS kcu USING (constraint_name, table_schema)
              JOIN information_schema.constraint_column_usage AS ccu USING (constraint_name)
             WHERE tc.constraint_type = 'FOREIGN KEY'
               AND ccu.table_schema = 'public'
               AND ccu.table_name = 'l10n_pl_bank_account_verification'
        """)
        table_column = self.env.cr.fetchall()
        if not table_column:
            return

        query = SQL(
            "DELETE FROM l10n_pl_bank_account_verification WHERE %s",
            SQL(" AND ").join(
                SQL(
                    "NOT EXISTS (SELECT 1 FROM %(table)s WHERE %(column)s = l10n_pl_bank_account_verification.id)",
                    table=SQL.identifier(table_name),
                    column=SQL.identifier(column_name),
                )
                for table_name, column_name in table_column
            )
        )
        self.env.cr.execute(query)

    @api.depends('verification_timestamp')
    def _compute_verification_date(self):
        for verification in self:
            verification.verification_date = verification.verification_timestamp.date()

    @api.depends('partner_bank_id')
    def _compute_partner_bank_account_number(self):
        for verification in self:
            # Only write at creation, to prevent account number changes
            if not verification.partner_bank_account_number:
                verification.partner_bank_account_number = verification.partner_bank_id.sanitized_account_number

    @api.depends('partner_id')
    def _compute_partner_vat(self):
        for verification in self:
            # Only write at creation, to prevent VAT changes
            if not verification.partner_vat:
                verification.partner_vat = verification.partner_id.vat

    def _l10n_pl_get_verification(self, partner_bank_data, date):
        """
        :param partner_bank_data: list(tuple(partner_id, partner_banks)): recordset of partner bank to get verification for by partner id
        :returns: A recordset of l10n_pl.bank.account.verification for all res.partner.bank in param
        """
        create_vals = []
        verifications = self.browse()
        partner_banks = self.env['res.partner.bank'].union(partner_bank for _partner_id, partner_bank in partner_bank_data)
        partners_without_bank_account = self.env['res.partner'].browse(partner_id for partner_id, bank_accounts in partner_bank_data if not bank_accounts)

        if partners_without_bank_account:
            # Create failed verifications for partners not having bank accounts
            verifications = self.search([
                ('partner_vat', 'in', partners_without_bank_account.mapped('vat')),
                ('partner_bank_account_number', '=', False),
                ('verification_status', 'in', ('incomplete_partner', 'not_found_partner', 'error')),
                ('verification_date', '=', date),
            ])
            # check if a failed verification already exists
            existing_failed_vat = set(verifications.mapped('partner_vat'))
            partners_to_create_verification_for = partners_without_bank_account.filtered(lambda partner: partner.vat not in existing_failed_vat)
            if partners_to_create_verification_for:
                create_vals += self._get_creation_vals('incomplete_partner', partners=partners_to_create_verification_for)

        partner_banks_to_check = self.env['res.partner.bank']
        if partner_banks:
            # create list of partner_bank to check
            all_partners = self.env['res.partner'].browse(partner_id for partner_id, bank_accounts in partner_bank_data if bank_accounts)
            all_partner_banks = all_partners.bank_ids
            # we query verifications for all partner banks so that if the API call returns information for one of the bank
            # account that was not requested, we can know if we need to create a verification
            verifications |= self.search([
                ('partner_bank_account_number', 'in', all_partner_banks.mapped('sanitized_account_number')),
                ('partner_vat', 'in', all_partner_banks.partner_id.mapped('vat')),
                ('verification_date', '=', date),
            ])

            partner_bank2verification = verifications.grouped(lambda verif: verif.partner_bank_account_number)
            for partner_bank in partner_banks:
                if self.env['res.partner']._is_vat_void(partner_bank.partner_id.vat):
                    create_vals += self._get_creation_vals('incomplete_partner', partner_banks=partner_bank)
                    continue

                # if partner bank already has a verification, check that status is failed and reason is not unknown (incomplete or not_found).
                # If so, no need to check as we made the search on the same vat/bank account -> the combination (vat/bank account) will still fail.
                # If the reason is unknown, let's check it again
                partner_bank_verif = partner_bank2verification.get(partner_bank.sanitized_account_number)
                if not partner_bank_verif or partner_bank_verif.verification_status == 'error':
                    partner_banks_to_check |= partner_bank

        if not partner_banks_to_check:
            if create_vals:
                # some partners without bank account or without vat need a failed verification to be created
                verifications |= self.sudo().create(create_vals)
            return verifications.filtered(
                lambda verif: verif.partner_bank_account_number in partner_banks.mapped('sanitized_account_number') or verif.partner_vat in partners_without_bank_account.mapped('vat'))

        # Create endpoints to call, API supports 30 vat numbers per request
        endpoints = {}  # {endpoint: recordset(res.partner)}
        partners_to_check = partner_banks_to_check.partner_id
        for i in range(0, len(partners_to_check), 30):
            partners = partners_to_check[i:i + 30]
            sanitized_vats = ",".join(partners.mapped(lambda partner: partner.vat.removeprefix('pl').removeprefix('PL')))
            endpoints[f'/search/nips/{sanitized_vats}'] = partners

        # Call API for every endpoint
        error_message = "Error while making request for partners %s, with endpoint %s"
        for endpoint, partners in endpoints.items():
            try:
                response = self._make_request(endpoint, params={'date': date})
                response_content = self._handle_response(response)
            except requests.RequestException:
                create_vals += self._get_creation_vals('error', partner_banks=partners.bank_ids)
                _logger.exception(error_message, partners.ids, endpoint)
                continue

            try:
                # Read received datas from API and create verifications
                datas = json.loads(response_content)['result']
                request_id = datas['requestId']
                timestamp = datetime.strptime(datas['requestDateTime'], "%d-%m-%Y %H:%M:%S")

                for entry in datas.get('entries'):
                    identifier = entry.get('identifier')
                    partner = self._get_partner_from_identifier(identifier)
                    if error := entry.get('error'):
                        status = 'error'
                        if error['code'] in ['WL-113', 'WL-115']:  # 113: incorrect format, 115: vat not found
                            status = 'not_found_partner'
                        create_vals += self._get_creation_vals(status, partner_banks=partner.bank_ids, timestamp=timestamp, request_id=request_id)
                        continue

                    subject = entry.get('subjects')
                    if not subject:  # case where code = 200, but subject is null or empty
                        create_vals += self._get_creation_vals('invalid', partner_banks=partner.bank_ids, timestamp=timestamp, request_id=request_id)
                        continue

                    subject = subject[0]
                    for partner_bank in partner.bank_ids:
                        # We take advantage of the API call to write verification on all bank accounts of this partner
                        # even if no check was requested for them
                        account_number = partner_bank.sanitized_account_number.removeprefix('pl').removeprefix('PL')
                        status = 'valid' if account_number in subject.get('accountNumbers', []) else 'invalid'
                        create_vals += self._get_creation_vals(
                            status,
                            partner_banks=partner_bank,
                            timestamp=timestamp,
                            request_id=request_id,
                        )

            except (KeyError, json.decoder.JSONDecodeError):
                create_vals += self._get_creation_vals('error', partner_banks=partners.bank_ids)
                _logger.exception(error_message, partners.ids, endpoint)
                continue

        # Filter create values if a verification already exists
        failed_verifications = verifications.filtered(lambda verif: verif.verification_status in ('incomplete_partner', 'partner_not_found', 'error'))
        partner_bank_vat2failed_verification = failed_verifications.grouped(lambda verif: (verif.partner_bank_account_number, verif.partner_vat))
        partner_bank_vat2verification = verifications.grouped(lambda verif: (verif.partner_bank_account_number, verif.partner_vat))
        to_create = []
        for vals in create_vals:
            # verif exists but failed so modify it to keep latest value
            if verif := partner_bank_vat2failed_verification.get((vals['partner_bank_account_number'], vals['partner_vat'])):
                verif.sudo().write(vals)

            # verification exists
            elif partner_bank_vat2verification.get((vals['partner_bank_account_number'], vals['partner_vat'])):
                continue

            # verification doesn't exist
            else:
                to_create.append(vals)

        if to_create:
            verifications |= self.sudo().create(to_create)
        # Filter out the verifications for the bank account linked to the partner but not requested in params
        return verifications.filtered(
            lambda verif: verif.partner_bank_account_number in partner_banks.mapped('sanitized_account_number') or verif.partner_vat in partners_without_bank_account.mapped('vat'))

    @api.model
    def _make_request(self, endpoint, params=None):
        """
        Send request to the government API
        :param endpoint: The endpoint to call in the API
        :param params: Params to include in request
        :return: response
        """
        params = params or {}
        url = urljoin('https://wl-api.mf.gov.pl/api', endpoint)
        response = requests.request(
            'GET',
            url,
            headers={'Content-Type': 'application/json'},
            params=params,
            timeout=5,
        )
        return response

    @api.model
    def _handle_response(self, response):
        """
        Handle response given by the API
        :param response: The response received by the API
        :return: Response content or raise an error
        """
        if response.status_code == 200:
            return response.content.decode()

        response.raise_for_status()

    def _get_creation_vals(self, status, partner_banks=[], partners=[], timestamp=None, request_id=False):
        """
        partners should be filled only for partners without bank accounts ('incomplete_partner')
        """
        assert not partners or partners and not partner_banks
        create_vals = []
        default_vals = {
            'verification_status': status,
            'verification_timestamp': timestamp or fields.Datetime.to_string(datetime.now(tz=ZoneInfo('Europe/Warsaw'))),
            'verification_request_id': request_id,
        }

        for partner_bank in partner_banks:
            vals = dict(default_vals)
            vals.update({
                'partner_bank_id': partner_bank.id,
                'partner_bank_account_number': partner_bank.sanitized_account_number,
                'partner_id': partner_bank.partner_id.id,
                'partner_vat': partner_bank.partner_id.vat,
            })
            create_vals.append(vals)

        # only for partners without bank accounts
        for partner in partners:
            vals = dict(default_vals)
            vals.update({
                'partner_id': partner.id,
                'partner_vat': partner.vat,
            })
            create_vals.append(vals)

        return create_vals

    @api.model
    def _get_partner_from_identifier(self, identifier):
        identifiers = [identifier, 'pl' + identifier, 'PL' + identifier]
        return self.env['res.partner'].search([('vat', 'in', identifiers)], limit=1)
