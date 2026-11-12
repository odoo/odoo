import base64
import logging
import tempfile
import time
import zipfile
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from dateutil.parser import parse

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_pl_edi.exceptions import KSeFRateLimitError
from odoo.addons.l10n_pl_edi.models.account_move import KSEF_FIRST_DAY
from odoo.addons.l10n_pl_edi_batch.tools.ksef_api_service import KsefApiServiceBatch as Service

_logger = logging.getLogger(__name__)

KSEF_WINDOW = 7
KSEF_IN_PROGRESS = 100
KSEF_READY = 200
KSEF_AFTER_HWM = 420
ODOO_ERROR = 999

CRON_REQUEST_TODAY = 'l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills'
CRON_REQUEST_HISTORIC = 'l10n_pl_edi_batch.ir_cron_request_historic'
CRON_CHECK_STATUS = 'l10n_pl_edi_batch.ir_cron_check_status'
CRON_DOWNLOAD = 'l10n_pl_edi_batch.ir_cron_download'
CRON_IMPORT = 'l10n_pl_edi_batch.ir_cron_import'

STATES = [
    ('requested', 'Requested'),
    ('downloading', 'Downloading'),
    ('downloaded', 'Downloaded'),
    ('done', 'Done'),
    ('failed', 'Failed'),
]

MAX_RETRIES = 9
HISTORIC_REQUEST_DELAY = timedelta(minutes=5)
IMPORT_SECONDS = 60


def ksef_midnight(day):
    """ Midnight of `day` in Polish time, in UTC without timezone, as Odoo stores datetimes. """
    polish_midnight = datetime(day.year, day.month, day.day, tzinfo=ZoneInfo('Europe/Warsaw'))
    utc_midnight = polish_midnight.astimezone(timezone.utc)
    return utc_midnight.replace(tzinfo=None)


def exp_backoff_delay(retry_count, base_delay=10):
    """ Exponential backoff: `base_delay` seconds, doubled at each retry. """
    return timedelta(seconds=base_delay * 2 ** retry_count)


class BatchDownload(models.Model):
    _name = 'l10n_pl_edi_batch.download'
    _description = "KSeF Batch Download"

    company_id = fields.Many2one(comodel_name='res.company', readonly=True, required=True)
    name = fields.Char("KSeF batch reference number", readonly=True, required=True)

    date_from = fields.Datetime(readonly=True, required=True)
    date_to = fields.Datetime(readonly=True, required=True)
    kind = fields.Selection(
        selection=[('today', 'Today'), ('historic', 'Historic')],
        compute='_compute_kind',
        search='_search_kind',
    )

    content = fields.Json(readonly=True)
    retry_count = fields.Integer(default=0, readonly=True, copy=False)

    # Symmetric encryption data, to keep invoices private between our request and KSeF's response
    raw_symmetric_key = fields.Binary("Batch symmetric key", readonly=True, groups='base.group_system')
    encrypted_symmetric_key = fields.Binary("Batch encrypted symmetric key", readonly=True, groups='base.group_system')
    raw_iv = fields.Binary("Batch iv", readonly=True, groups='base.group_system')

    # Parts of the ZIP to be downloaded
    part_ids = fields.One2many(
        comodel_name='l10n_pl_edi_batch.part',
        string='KSeF Batch parts',
        readonly=True,
        copy=False,
        inverse_name='batch_id',
    )

    # Computed fields
    state = fields.Selection(selection=STATES, compute='_compute_state', search='_search_state')
    date_expiry = fields.Datetime(compute='_compute_date_expiry')
    is_expired = fields.Boolean(compute='_compute_is_expired', search='_search_expired')
    error = fields.Char("KSeF batch download error", compute='_compute_error')

    @api.depends('content')
    def _compute_error(self):
        for record in self:
            ksef_status = (record.content or {}).get('status', {})
            code = ksef_status.get('code')
            if not code or code in (KSEF_IN_PROGRESS, KSEF_READY):
                record.error = False
                continue
            description = ksef_status.get('description')
            lines = [f"{code}: {description}" if description else str(code)] + (ksef_status.get('details') or [])
            record.error = '\n'.join(lines)

    @api.model
    def _get_kind(self, date_to, create_date):
        """ A today batch ends when it's requested; a historic one ends at least a day before. """
        if date_to and date_to <= create_date - timedelta(hours=24):
            return 'historic'
        return 'today'

    @api.depends('date_to', 'create_date')
    def _compute_kind(self):
        for record in self:
            record.kind = record._get_kind(record.date_to, record.create_date or fields.Datetime.now())

    def _search_kind(self, operator, value):
        if operator not in ('=', '!=', 'in', 'not in'):
            raise NotImplementedError(self.env._("Operation not supported"))
        values = value if isinstance(value, (list, tuple)) else [value]
        batches = self.search([]).filtered(lambda batch: batch.kind in values)
        if operator in ('=', 'in'):
            return [('id', 'in', batches.ids)]
        return [('id', 'not in', batches.ids)]

    def _get_state_by_code(self, code):
        self.ensure_one()
        if code == KSEF_AFTER_HWM:  # `from` is after KSeF's high water mark: nothing new is stored yet
            return 'done'
        if code not in (KSEF_IN_PROGRESS, KSEF_READY) or self.retry_count > MAX_RETRIES:
            return 'failed'
        elif code == KSEF_IN_PROGRESS:
            return 'requested'
        elif code == KSEF_READY and self.part_ids:
            parts_missing = self.part_ids.filtered(lambda part: not part.with_context(bin_size=True).decrypted_file)
            if parts_missing:
                return 'failed' if self.is_expired else 'downloading'
            return 'downloaded'
        return 'done'

    @api.depends('content', 'retry_count', 'part_ids.decrypted_file')
    def _compute_state(self):
        for batch in self:
            code = (batch.content or {}).get('status', {}).get('code') or KSEF_IN_PROGRESS
            batch.state = batch._get_state_by_code(code)

    def _search_state(self, operator, value):
        if operator not in ('=', '!=', 'in', 'not in'):
            raise NotImplementedError(self.env._("Operation not supported"))
        values = value if isinstance(value, (list, tuple)) else [value]
        batches = self.search([]).filtered(lambda batch: batch.state in values)
        if operator in ('=', 'in'):
            return [('id', 'in', batches.ids)]
        return [('id', 'not in', batches.ids)]

    @api.depends('content')
    def _compute_date_expiry(self):
        for record in self:
            date_expiry = (record.content or {}).get('packageExpirationDate')
            if date_expiry:
                date_expiry = parse(date_expiry).astimezone(timezone.utc).replace(tzinfo=None)
            record.date_expiry = date_expiry or False

    def _search_expired(self, operator, value):
        if operator not in ('=', '!='):
            raise NotImplementedError(self.env._("Operation not supported"))
        target_value = bool(value) if operator == '=' else not bool(value)
        batches = self.search([]).filtered(lambda batch: batch.is_expired == target_value)
        return [('id', 'in', batches.ids)]

    @api.depends('date_expiry', 'retry_count')
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_expired = (
                (record.date_expiry and record.date_expiry < now)
                or record.retry_count > MAX_RETRIES
            )

    @api.ondelete(at_uninstall=False)
    def _unlink_parts(self):
        """ Unlink the parts through the ORM, so that their attachments are removed too. """
        self.part_ids.unlink()

    @api.autovacuum
    def _gc_batch_downloads(self):
        """ Delete the batches done or failed more than 30 days ago, with their parts.
            Their last write stands for the time they finished. """
        if finished_batches := self.sudo().search([
            ('write_date', '<', fields.Datetime.now() - timedelta(days=30)),
            ('state', 'in', ('done', 'failed')),
        ]):
            finished_batches.unlink()

    def _commit(self):
        if self.env['account.move']._can_commit():
            self.env.cr.commit()

    def _rollback(self):
        if self.env['account.move']._can_commit():
            self.env.cr.rollback()

    @api.model
    def _get_company_batches(self, company, state):
        return self.search([('company_id', '=', company.id), ('state', '=', state)], order='date_to desc')

    @api.model
    def _create_batch_download(self, company, date_from, date_to):
        """ Ask KSeF for an export of the company's bills between the two dates
            Save the batch as requested, and have the status cron check it.
        """
        service = Service(company)
        encryption_data = service._create_encryption_data()
        batch_data = service.download_batch_request(date_from, date_to, encryption_data)
        batch = self.create({
            'company_id': company.id,
            'name': batch_data['referenceNumber'],
            'date_from': date_from,
            'date_to': date_to,
            'raw_symmetric_key': encryption_data['raw_symmetric_key'],
            'encrypted_symmetric_key': encryption_data['encrypted_symmetric_key'],
            'raw_iv': encryption_data['raw_iv'],
        }).with_env(self.env)
        self.env.ref(CRON_CHECK_STATUS)._trigger()
        return batch

    def _run_for_all_companies(self, method, cron_xmlid, company_domain=None):
        """ Every KSeF cron must:
            - run per each company that has the batch download enabled and an access_token available
            - on rate limit hit, rollback and be retriggered after ``retry_after`` seconds
            - commit per company
            - notify the progress once for all companies: ``method`` returns the work left for its company
              when it did some, None otherwise
        """
        retry_at = False
        done = remaining = 0
        companies = self.env['res.company'].search([
            ('l10n_pl_edi_access_token', '!=', False),
            *(company_domain or []),
        ])

        for company in companies:
            try:
                company_remaining = method(company)
                self._commit()
                if company_remaining is not None:
                    done += 1
                    remaining += company_remaining
            except KSeFRateLimitError as e:
                self._rollback()
                current_retry_at = fields.Datetime.now() + timedelta(seconds=e.retry_after or 60)
                retry_at = min(retry_at, current_retry_at) if retry_at else current_retry_at
                _logger.info(
                    "KSeF rate limit reached for company %s, running %s again at %s",
                    company.display_name, cron_xmlid, retry_at,
                )

        if retry_at:
            self.env.ref(cron_xmlid)._trigger(at=retry_at)
        if done:
            self.env['ir.cron']._notify_progress(done=done, remaining=remaining)

    @api.model
    def _cron_request_today(self):
        self._run_for_all_companies(self._request_today, CRON_REQUEST_TODAY)

    @api.model
    def _request_today(self, company):
        """ Request the most recent bills, up to now: from where the last done today batch is complete
            (where its export stopped if truncated, its high water mark otherwise), or from yesterday at Polish midnight.
        """
        yesterday = ksef_midnight(fields.Date.today() - timedelta(days=1))
        date_from = yesterday
        last_done_batch = self.search([
            ('company_id', '=', company.id),
            ('kind', '=', 'today'),
            ('state', '=', 'done'),
            ('create_date', '>=', yesterday),
        ], order='create_date desc', limit=1)
        package = (last_done_batch.content or {}).get('package') or {}
        date_key = 'lastPermanentStorageDate' if package.get('isTruncated') else 'permanentStorageHwmDate'
        if last_storage_date := package.get(date_key):
            last_storage_date = parse(last_storage_date).astimezone(timezone.utc).replace(tzinfo=None)
            date_from = max(yesterday, last_storage_date)
        self._create_batch_download(company, date_from=date_from, date_to=fields.Datetime.now())

    @api.model
    def _cron_request_historic(self):
        """ Request the past invoices """
        pending_companies_ids = self.search([
            ('kind', '=', 'historic'),
            ('state', 'in', ('requested', 'downloading', 'downloaded')),
        ]).mapped("company_id.id")

        def request_historic(company):
            last_batch = self.search([
                ('company_id', '=', company.id),
                ('kind', '=', 'historic'),
            ], order='create_date desc, id desc', limit=1)
            attempts = last_batch.state == 'failed' and self.search_count([
                ('company_id', '=', company.id),
                ('date_from', '=', last_batch.date_from),
                ('date_to', '=', last_batch.date_to),
            ])
            if attempts and attempts < MAX_RETRIES:
                # the last window failed: request it again
                self._create_batch_download(company, last_batch.date_from, last_batch.date_to)
            else:
                if attempts:
                    _logger.error("KSeF batch window %s - %s failed %s times, it is not requested again: %s",
                                  last_batch.date_from, last_batch.date_to, attempts, last_batch.error)
                day_to = company.l10n_pl_edi_batch_historic_date
                day_from = max(day_to - timedelta(days=KSEF_WINDOW), KSEF_FIRST_DAY)
                self._create_batch_download(company, ksef_midnight(day_from), ksef_midnight(day_to))
                company.l10n_pl_edi_batch_historic_date = day_from

        self._run_for_all_companies(
            request_historic,
            CRON_REQUEST_HISTORIC,
            company_domain=[
                ('id', 'not in', pending_companies_ids),
                ('l10n_pl_edi_batch_historic_date', '>', KSEF_FIRST_DAY),
            ])

    @api.model
    def _cron_check_status(self):
        """ Ask KSeF for the status of the latest requested batch of each company.
            Still 100: count a retry, and check again after 10 * 2**retry_count seconds;
            after the last retry, the batch fails.
        """

        def check_status(company):
            batches = self._get_company_batches(company, 'requested')
            if batch := batches[:1]:
                data = Service(company).download_batch_status(batch.name)
                old_date_to = batch.date_to
                package = data['content'].get('package') or {}
                if is_truncated := package.get('isTruncated'):
                    data['date_to'] = parse(package['lastPermanentStorageDate']).astimezone(timezone.utc).replace(tzinfo=None)

                batch.update(data)
                if batch.state == 'downloading':
                    batch.retry_count = 0  # the download counts its own retries
                    self.env.ref(CRON_DOWNLOAD)._trigger()
                    # A truncated export: this batch now ends where KSeF stopped, request the rest
                    if is_truncated:
                        self._create_batch_download(company, batch.date_to, old_date_to)
                elif batch.state == 'done' and batch.kind == 'historic':
                    # empty window: request the next one
                    self._trigger_delayed(CRON_REQUEST_HISTORIC, HISTORIC_REQUEST_DELAY)
                elif batch.state == 'requested':
                    if batch.retry_count <= MAX_RETRIES:
                        batch.retry_count += 1
                        self._trigger_delayed(CRON_CHECK_STATUS, delay=exp_backoff_delay(batch.retry_count))
                elif batch.state == 'failed' and batch.kind == 'historic':
                    # request the same window again
                    self._trigger_delayed(CRON_REQUEST_HISTORIC, HISTORIC_REQUEST_DELAY)

                # this batch is no longer waiting: check the next requested one right away
                if batch.state != 'requested' and len(batches) > 1:
                    self.env.ref(CRON_CHECK_STATUS)._trigger()

        self._run_for_all_companies(check_status, CRON_CHECK_STATUS)

    @api.model
    def _cron_download(self):
        def do_download(company):
            if batch := self._get_company_batches(company, 'downloading')[:1]:
                missing_parts = batch.part_ids.with_context(bin_size=True).filtered(lambda part: not part.decrypted_file)
                try:
                    missing_parts[:1]._download()
                except UserError as e:
                    _logger.info("KSeF batch %s download failed (retry %s): %s", batch.name, batch.retry_count + 1, e)
                    batch._retry_download(str(e))
                    return
                if batch.state != 'downloading':
                    self.env.ref(CRON_IMPORT)._trigger()
                return len(missing_parts) - 1
        self._run_for_all_companies(do_download, CRON_DOWNLOAD)

    @api.model
    def _cron_import(self):
        deadline = time.monotonic() + IMPORT_SECONDS

        def do_import(company):
            batches = self._get_company_batches(company, 'downloaded')
            if not batches:
                return
            batch = batches[:1]

            AccountMove = self.env['account.move'].with_company(batch.company_id)
            with tempfile.TemporaryFile(mode='w+b') as zip_stream:
                # merge
                for part in batch.part_ids.sorted('part_number'):
                    content = base64.b64decode(part.decrypted_file)
                    zip_stream.write(content)
                zip_stream.seek(0)

                # unzip
                try:
                    zip_file = zipfile.ZipFile(zip_stream, 'r')
                except zipfile.BadZipFile as e:
                    batch.part_ids.decrypted_file = False
                    batch.part_ids.invalidate_recordset(['decrypted_file'])
                    batch._retry_download(self.env._("The KSeF batch ZIP is corrupt: %s", e))
                    return

                with zip_file:
                    # exclude already imported files
                    ksef_numbers = {
                        name.removesuffix('.xml')
                        for name in zip_file.namelist()
                        if name.endswith('.xml')
                    }
                    existing_ksef_numbers = set(AccountMove.search([
                        ('l10n_pl_edi_number', 'in', list(ksef_numbers)),
                        ('company_id', '=', batch.company_id.id),
                        ('move_type', '=', 'in_invoice'),
                        ('l10n_pl_edi_status', 'not in', ('fetch_ready', 'fetch_failed')),
                    ]).mapped('l10n_pl_edi_number'))

                    # loop over zipped files
                    new_ksef_numbers = ksef_numbers - existing_ksef_numbers
                    half_fetched_bills = AccountMove.search([
                        ('l10n_pl_edi_number', 'in', list(new_ksef_numbers)),
                        ('company_id', '=', batch.company_id.id),
                        ('move_type', '=', 'in_invoice'),
                    ]).grouped('l10n_pl_edi_number')
                    for count, ksef_number in enumerate(new_ksef_numbers, 1):

                        # create the move (or fill the half-fetched one) and the attachment
                        move = half_fetched_bills.get(ksef_number) or AccountMove.create([{'move_type': 'in_invoice', 'l10n_pl_edi_number': ksef_number}])
                        attachment = self.env['ir.attachment'].create({
                            'name': f"KSeF-{ksef_number.replace('/', '_')}.xml",
                            'description': self.env._('KSeF Fetched Invoice XML'),
                            'mimetype': 'application/xml',
                            'company_id': batch.company_id.id,
                            'res_model': move._name,
                            'res_id': move.id,
                            'raw': zip_file.read(ksef_number + '.xml'),
                        })

                        # import
                        move.message_post(
                            body=self.env._("KSeF bill %s has been attached for import", ksef_number),
                            attachment_ids=attachment.ids,
                        )

                        # fetched even if the import failed: the XML is attached, the error is in the chatter
                        move.l10n_pl_edi_status = 'fetched'
                        self._commit()

                        # out of time: the next run imports the rest
                        if count < len(new_ksef_numbers) and time.monotonic() >= deadline:
                            self.env.ref(CRON_IMPORT)._trigger()
                            return

                batch.part_ids.unlink()

            if batch.kind == 'historic':
                # request the next window
                self._trigger_delayed(CRON_REQUEST_HISTORIC, HISTORIC_REQUEST_DELAY)
            return len(batches) - 1

        self._run_for_all_companies(do_import, CRON_IMPORT)

    @api.model
    def _trigger_delayed(self, cron_xmlid, delay):
        """ Run the cron after `delay`. """
        self.env.ref(cron_xmlid)._trigger(at=fields.Datetime.now() + delay)

    def _retry_download(self, error):
        """ Count a download retry, and download again once due. After the last retry, the batch fails
            with `error`, and a historic window is requested again in a while. """
        self.ensure_one()
        if self._raise_retry_count(error):
            self._trigger_delayed(CRON_DOWNLOAD, delay=exp_backoff_delay(self.retry_count))
        elif self.kind == 'historic':
            self._trigger_delayed(CRON_REQUEST_HISTORIC, HISTORIC_REQUEST_DELAY)

    def _raise_retry_count(self, error):
        """ Count a retry, and return whether the batch can be retried. After the last retry, or once the package
            expired with parts still missing, the batch fails with `error`. """
        self.ensure_one()
        self.retry_count += 1
        if failed := (self.state == 'failed'):
            self.content = {
                **(self.content or {}),
                'status': {'code': ODOO_ERROR, 'description': "Odoo Error", 'details': [error]},
            }
        return not failed
