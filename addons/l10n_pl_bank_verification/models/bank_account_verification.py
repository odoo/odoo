import json
import logging
import requests

from collections import defaultdict
from urllib.parse import urljoin
from werkzeug import urls

from odoo import api, fields, models
from odoo.tools import index_exists, LazyTranslate, SQL

_logger = logging.getLogger(__name__)
_lt = LazyTranslate(__name__)

PL_PROXY_ERROR_CODES = {
    'invalid_date_format': _lt("Invalid date format. Expected format: 'YYYYMMDD'"),
    'invalid_date': _lt("IAP has no data for today (yet), cron will try again later or tomorrow."),
    'invalid_combination': _lt("Invalid combination provided, please follow format : <nip:bank_account_number> (\\d{10}:\\d{26},?){1,30}>"),
}


class BankAccountVerification(models.Model):
    _name = 'l10n_pl.bank.account.verification'
    _description = 'PL Bank Account Verification'

    verification_status = fields.Selection(
        selection=[
            ('valid', 'Valid'),
            ('invalid', 'Invalid'),  # Bank account not referenced (in gov files) for partner's vat number
            ('incomplete_partner', 'Incomplete partner'),  # Inside Odoo, no IAP call
            ('error', 'Pending validation'),  # IAP called -> error
        ],
        string="Verification Status",
        readonly=True,
        required=True,
        help="Flag the payment verification status with one of the following:\n"
            "- Valid: The partner VAT is linked to the bank account used for this payment.\n"
            "- Invalid: The partner VAT is not linked to the bank account used for this payment.\n"
            "- Incomplete partner: The partner has no VAT or no bank account.\n"
            "- Pending validation: An error occurred during check with IAP. It will be checked again automatically later.\n"
    )
    # stored in UTC, timestamp when the verification is created or modified
    verification_timestamp = fields.Datetime("Verification Timestamp", readonly=True)
    # Data validity date, if IAP respond without error the answer are valid for the date requested
    verification_date = fields.Date(
        index=False,
    )
    # TODO rename to digest in master
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

    def _auto_init(self):
        super()._auto_init()
        if not index_exists(self.env.cr, 'l10n_pl_unique_bank_account_verificattion'):
            self.env.cr.execute("""
                CREATE UNIQUE INDEX l10n_pl_unique_bank_account_verificattion
                                 ON l10n_pl_bank_account_verification(verification_date, partner_bank_account_number, partner_vat)
            """)

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

    @api.depends('partner_bank_id')
    def _compute_partner_bank_account_number(self):
        for verification in self:
            # Only write at creation, to prevent account number changes
            if not verification.partner_bank_account_number:
                verification.partner_bank_account_number = verification.partner_bank_id.sanitized_acc_number

    @api.depends('partner_id')
    def _compute_partner_vat(self):
        for verification in self:
            # Only write at creation, to prevent VAT changes
            if not verification.partner_vat:
                verification.partner_vat = verification.partner_id.vat

    @api.model
    def _cron_check_pending_verification(self):
        pending_verifications = self.search([('verification_status', '=', 'error')])
        if pending_verifications:
            self._l10n_pl_get_verification(
                [(v.partner_id.id, v.partner_bank_id) for v in pending_verifications],
                fields.Date.context_today(self.with_context(tz='Europe/Warsaw')),
            )

    def _l10n_pl_get_verification(self, partner_bank_data, date):
        """
        :param partner_bank_data: list(tuple(partner_id, partner_banks)): partner banks to get verification for, associated with partner id
        :returns: A recordset of l10n_pl.bank.account.verification for all res.partner.bank in param
        """
        # you shouldn't have 2 combinations with the same partner and
        # one empty bank account [(1, res.partner.bank(1)), (1, res.partner.bank())]
        partner_to_banks = defaultdict(list)
        invalid_partner_ids = []
        for partner_id, bank in partner_bank_data:
            partner_to_banks[partner_id].append(bank)

        create_vals = []
        verifications = self.browse()
        partner_map = self.env['res.partner'].browse(partner_id for partner_id, bank_account in partner_bank_data).grouped('id')
        for partner_id, banks in partner_to_banks.items():
            valid_banks = [bank for bank in banks if bank]
            if 1 < len(banks) != len(valid_banks):
                # partner has multiple banks to check and at least one of them is null, should never happen: bad args to the method
                invalid_partner_ids.append(partner_id)
                create_vals += self._get_creation_vals('error', partner_banks=valid_banks)  # should never happen
                create_vals += self._get_creation_vals('incomplete_partner', partner_ids=[partner_id])
            elif len(banks) == 1 and not banks[0] or partner_map.get(partner_id).vat in [False, '/', 'na', 'NA']:
                # partner has no bank or partner has no vat
                invalid_partner_ids.append(partner_id)
                create_vals += self._get_creation_vals('incomplete_partner', partner_ids=[partner_id])

        if invalid_partner_ids:
            # existing failed verifications
            verifications |= self.search([
                ('partner_id', 'in', invalid_partner_ids),
                ('partner_vat', 'in', [False, '/', 'na', 'NA']),
                ('partner_bank_id', '=', False),
                ('partner_bank_account_number', '=', False),
            ])
            verification_failed_map = verifications.grouped(lambda verif: verif.partner_id.id)

            # filter out creation vals for partner that already have failed verification
            create_vals = [vals for vals in create_vals if vals['partner_id'] not in verification_failed_map]

        # structure datas like {partner_id: (res.partner, recordset(res.partner.bank))}
        datas = {
            partner_id: (partner_map.get(partner_id), self.env['res.partner.bank'].union(*list(banks)))
            for partner_id, banks in partner_to_banks.items()
            if partner_id not in invalid_partner_ids
        }

        if not datas:
            # early return
            if create_vals:
                verifications |= self.sudo().create(create_vals)
            return verifications

        remaining_partners = self.env['res.partner'].browse(datas.keys())
        remaining_banks = self.env['res.partner.bank'].union(*[banks for _partner, banks in datas.values()])

        # existing verifications for remaining partners/banks
        common_domain = [
            ('partner_id', 'in', list(datas.keys())),
            ('partner_vat', 'in', remaining_partners.mapped('vat')),
            ('partner_bank_id', 'in', remaining_banks.ids),
            ('partner_bank_account_number', 'in', remaining_banks.mapped('sanitized_acc_number')),
        ]
        verifications |= self.search(common_domain + [('verification_status', 'in', ['valid', 'invalid']), ('verification_date', '=', date)])
        verification_map = verifications.grouped(lambda verif: (verif.partner_id, verif.partner_bank_id))
        # get verifications in 'error' state whatever the date, and update the timestamp
        # we don't include them in verification_map to force to check them again
        pending_verifications = self.search(common_domain + [('verification_status', '=', 'error')])
        pending_verifications.sudo().write({'verification_timestamp': fields.Datetime.now()})
        verifications |= pending_verifications
        pending_verifications_map = pending_verifications.grouped(lambda verif: (verif.partner_id, verif.partner_bank_id))

        combinations_to_check = []
        for partner_id, (partner, banks) in datas.items():
            for bank in banks:
                if not verification_map.get((partner, bank)):
                    combinations_to_check.append((partner, bank))

        if not combinations_to_check:
            if create_vals:
                verifications |= self.sudo().create(create_vals)
            return verifications

        # Create endpoints to call, IAP supports 30 combinations per request
        endpoints = {}  # {endpoint: recordset(res.partner.bank)}
        for i in range(0, len(combinations_to_check), 30):
            tmp_endpoint = []
            bank_accounts = self.env['res.partner.bank'].browse()
            for partner, bank_account in combinations_to_check[i:i + 30]:
                vat = partner.vat.removeprefix('pl').removeprefix('PL')
                account_number = bank_account.sanitized_acc_number.removeprefix('pl').removeprefix('PL')
                tmp_endpoint.append(f"{vat}:{account_number}")
                bank_accounts |= bank_account
            endpoint = ','.join(tmp_endpoint)
            endpoints[endpoint] = bank_accounts

        # Call IAP for every endpoint
        for endpoint, banks in endpoints.items():
            response = False
            try:
                response = self._make_request(endpoint, date)
                response_content = self._handle_response(response)
            except (requests.RequestException, ValueError, json.decoder.JSONDecodeError) as e:
                banks_to_create_verification_for = [bank for bank in banks if not pending_verifications_map.get((bank.partner_id, bank))]
                create_vals += self._get_creation_vals('error', partner_banks=banks_to_create_verification_for)
                _logger.warning("Error while making request with endpoint %s, and date %s", endpoint, date)
                if isinstance(e, requests.exceptions.ConnectionError):
                    _logger.warning("Cannot reach iap server")
                    continue
                msg = isinstance(response, requests.Response) and PL_PROXY_ERROR_CODES.get(json.loads(response.content.decode())['error'])
                _logger.warning(msg or "Unknown error")
                continue

            try:
                # Read received datas from IAP and create verifications
                bank_account_map = endpoints[endpoint].grouped(lambda account: account.sanitized_acc_number.removeprefix('pl').removeprefix('PL'))
                for val in response_content:
                    partner = self._get_partner_from_identifier(val['vat'])
                    bank_account = bank_account_map.get(val['bank_account'])
                    status = 'valid' if val['status'] else 'invalid'
                    digest = val['hash'] or False
                    temp_create_vals = self._get_creation_vals(status, partner_banks=[bank_account], digest=digest, date=date)
                    verif = pending_verifications_map.get((partner, bank_account))
                    if verif:
                        verif.sudo().write(temp_create_vals[0])
                    else:
                        create_vals += temp_create_vals

            except KeyError:
                banks_to_create_verification_for = [bank for bank in banks if not pending_verifications_map.get((bank.partner_id, bank))]
                create_vals += self._get_creation_vals('error', partner_banks=banks_to_create_verification_for)
                _logger.warning("Error while decoding response for %s, with date %s", endpoint, date)
                continue

        verifications |= self.sudo().create(create_vals)
        return verifications

    @api.model
    def _make_request(self, endpoint, date):
        """Send request to IAP and returns the response"""
        if '://' in endpoint or endpoint.startswith('//'):
            raise ValueError("Invalid Polish bank verification API endpoint")
        base_url = self.env['ir.config_parameter'].sudo().get_param('l10n_pl_iap_bank_verification', 'https://iap-services.odoo.com')
        url = urljoin(base_url, '/iap/l10n_pl_edi/1/check_vat')
        url = f"{url}?{urls.url_encode({'date': date.strftime('%Y%m%d'), 'combinations': endpoint})}"
        response = requests.get(url, timeout=5)
        return response

    @api.model
    def _handle_response(self, response):
        """
        Handle response given by the API
        :param response: The response received by the API
        :return: Response content or raise an error
        """
        if response.status_code == 200:
            return response.json()

        response.raise_for_status()

    def _get_creation_vals(self, status, partner_banks=[], partner_ids=[], date=False, digest=False):
        """
        Build a list of creation vals. partner_banks should always be provided, only empty in case
        the partner has no bank account linked and then 'partner_ids' arg should be filled (one or the other)
        :param status: status, see verification_status selection
        :param partner_banks: list of bank accounts: can only be empty when partners have no bank account linked
        :param partner_ids: list of partner **ids** that have no bank account linked
        :param date: date of the data validity (only provided for verifications with 'valid' or 'invalid' state)
        :param digest: the digest of the combination
        :returns: list of creation vals
        """
        assert not partner_ids or partner_ids and not partner_banks
        create_vals = []
        default_vals = {
            'verification_status': status,
            'verification_timestamp': fields.Datetime.now(),
            'verification_date': date,
        }

        # partners with a linked bank account, having a valid vat
        for partner_bank in partner_banks:
            vals = dict(default_vals)
            vals.update({
                'partner_bank_id': partner_bank.id,
                'partner_bank_account_number': partner_bank.sanitized_acc_number,
                'partner_id': partner_bank.partner_id.id,
                'partner_vat': partner_bank.partner_id.vat,
                'verification_request_id': digest
            })
            create_vals.append(vals)

        # partners with no bank account or no valid vat
        for partner_id in partner_ids:
            vals = dict(default_vals)
            vals['partner_id'] = partner_id
            create_vals.append(vals)

        return create_vals

    @api.model
    def _get_partner_from_identifier(self, identifier):
        identifiers = [identifier, 'pl' + identifier, 'PL' + identifier]
        return self.env['res.partner'].search([('vat', 'in', identifiers)], limit=1)
