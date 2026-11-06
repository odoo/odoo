import base64
import logging
import tempfile
import zipfile
from datetime import timedelta, timezone

from dateutil.parser import parse

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import str2bool

from odoo.addons.l10n_pl_edi.exceptions import KSeFRateLimitError
from odoo.addons.l10n_pl_edi_batch.tools.ksef_api_service import KsefApiServiceBatch as Service

_logger = logging.getLogger(__name__)

KSEF_WINDOW = 7
KSEF_FIRST_DAY = fields.Date.from_string('2026-01-31')

KSEF_IN_PROGRESS = 100
KSEF_READY = 200
ODOO_ERROR = 999

STATES = [
    ('requested', 'Requested'),
    ('downloading', 'Downloading'),
    ('downloaded', 'Downloaded'),
    ('done', 'Done'),
    ('failed', 'Failed'),
]

MAX_RETRIES = 9


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

    def _compute_state_by_code(self, code):
        self.ensure_one()
        if self.is_expired or code not in (KSEF_IN_PROGRESS, KSEF_READY):
            return 'failed'
        elif code == KSEF_IN_PROGRESS:
            return 'requested'
        elif code == KSEF_READY and self.parts_ids:
            parts_missing = self.parts_ids.filtered(lambda part: not part.with_context(bin_size=True).decrypted_file)
            return 'downloading' if parts_missing else 'downloaded'
        return 'done'

    @api.depends('content', 'retry_count', 'part_ids.decrypted_file')
    def _compute_state(self):
        for batch in self:
            code = (batch.content or {}).get('status', {}).get('code') or KSEF_IN_PROGRESS
            batch.state = batch._compute_state_by_code(code)

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

    @api.model
    def _is_enabled(self):
        """ The batch download replaces the single-invoice download only when explicitly enabled. """
        value = self.env['ir.config_parameter'].sudo().get_param('l10n_pl_edi_batch.enabled', 'False')
        return str2bool(value, default=False)

    def _commit(self):
        if self.env['account.move']._can_commit():
            self.env.cr.commit()

    def _rollback(self):
        if self.env['account.move']._can_commit():
            self.env.cr.rollback()

    @api.model
    def _create_batch_download(self, company, date_from, date_to):
        """ Ask KSeF for an export of the company's bills between the two dates
            Save the batch as requested, and have the status cron check it.
        """
        service = Service(company)
        encryption_data = service._create_encryption_data()
        batch_data = service.download_batch_request(date_from, date_to, encryption_data)
        batch = self.sudo().create({
            'company_id': company.id,
            'name': batch_data['referenceNumber'],
            'date_from': date_from,
            'date_to': date_to,
            'raw_symmetric_key': encryption_data['raw_symmetric_key'],
            'encrypted_symmetric_key': encryption_data['encrypted_symmetric_key'],
            'raw_iv': encryption_data['raw_iv'],
        }).with_env(self.env)
        batch._trigger_cron_when_due('l10n_pl_edi_batch.ir_cron_check_status')
        return batch

    def _run_for_all_companies(self, method, cron_xmlid, company_domain=None):
        """ Every KSeF cron must:
            - only run if the batched download parameter is up
            - run per each company that has an access_token available
            - on rate limit hit, rollback and be retriggered after ``retry_after`` seconds
            - commit per company
        """
        if not self._is_enabled():
            return
        retry_at = False
        CompanySudo = self.env['res.company'].sudo()
        companies = CompanySudo.search([('l10n_pl_edi_access_token', '!=', False), *(company_domain or [])])

        for company in companies:
            try:
                method(self, company)
                self._commit()
            except KSeFRateLimitError as e:
                self._rollback()
                current_retry_at = fields.Datetime.now() + timedelta(seconds=e.retry_after)
                retry_at = min(retry_at, current_retry_at) if retry_at else current_retry_at

        if retry_at:
            _logger.info(
                "KSeF rate limit reached for company %s, running %s again at %s",
                company.display_name, cron_xmlid, retry_at,
            )
            self.env.ref(cron_xmlid)._trigger(at=retry_at)

    @api.model
    def _cron_request_today(self):
        """ Request yesterday and today's invoices """
        now = fields.Datetime.now()
        yesterday = fields.Datetime.start_of(now, 'day') - timedelta(days=1)

        def request_today(company):
            self._create_batch_download(company, date_from=yesterday, date_to=now)

        self._run_for_all_companies(request_today, 'l10n_pl_edi.cron_l10n_pl_edi_ksef_download_bills')

    @api.model
    def _cron_request_historic(self):
        """ Request the past invoices """
        first_day = fields.Datetime.to_datetime(KSEF_FIRST_DAY)

        pending_companies_ids = self.sudo().search([
            ('kind', '=', 'historic'),
            ('state', 'in', ('requested', 'downloading', 'downloaded')),
        ]).mapped("company_id.id")

        def request_historic(company):
            date_to = company.l10n_pl_edi_batch_historic_date
            date_from = max(date_to - timedelta(days=KSEF_WINDOW), first_day)

            # Find out if the period ALREADY has fetched invoices.
            period_has_fetched_invoices = self.env['account.move'].search([
                ('company_id', '=', company.id),
                ('move_type', '=', 'in_invoice'),
                ('date', '>=', date_from),
                ('date', '<', date_to),
                ('l10n_pl_edi_number', '!=', False),
                ('l10n_pl_edi_status', '=', 'fetched'),
            ])

            # Download invoices for this period
            self._create_batch_download(company, date_from, date_to)

            # In that case, it's the last we download, as the rest is already done by non-batched download
            if period_has_fetched_invoices:
                company.l10n_pl_edi_batch_historic_date = first_day

        self._run_for_all_companies(
            request_historic,
            'l10n_pl_edi_batch.ir_cron_request_historic',
            company_domain=[
                ('id', 'not in', pending_companies_ids),
                ('l10n_pl_edi_batch_historic_date', '>', first_day),
            ])

    @api.model
    def _cron_check_status(self):
        """ Ask KSeF for the status of each due requested batch, and commit after each one.
            Still 100, or a KSeF error: count a retry, and check again once the batch is due;
            after the last retry, the batch fails.
        """

        def check_status(company):
            if batch := self.search([('company_id', '=', company.id), ('state', '=', 'requested')], order='date_to desc', limit=1):
                service = Service(company)
                data = service.download_batch_status(batch.name)
                code = data['content'].get('status', {}).get('code') or KSEF_IN_PROGRESS

                state = batch._compute_state_by_code(code)
                if state == 'downloading':
                    self.env.ref('l10n_pl_edi_batch.ir_cron_download')._trigger()
                    # In case it's truncated, we create another batch to get the rest
                    if batch.kind == 'historic':
                        package = (data.get('content') or {}).get('package', {})
                        if package.get('isTruncated'):
                            last_date = parse(package['lastInvoicingDate']).astimezone(timezone.utc).replace(tzinfo=None)
                            old_date_to = self.date_to
                            data['date_to'] = last_date
                            self._create_batch_download(batch.company_id, last_date, old_date_to)
                elif state == 'requested':
                    batch.retry_count += 1
                    batch._trigger_cron_when_due('l10n_pl_edi_batch.ir_cron_check_status')

                batch.update(data)

    def _get_wait(self):
        """ A batch waits `10 * 2 ** retry_count` seconds after its last write before its next try. """
        self.ensure_one()
        return timedelta(seconds=10 * 2 ** self.retry_count)

    def _trigger_cron_when_due(self, cron_ref):
        """ Run the cron once the batch, just written, is due again. """
        self.env.ref(cron_ref)._trigger(at=fields.Datetime.now() + self._get_wait())

    def _count_retry(self, error, cron_ref):
        """ Count a retry, and run the cron again once the batch is due. After the last retry, or once the package
            expired with parts still missing, the batch fails with `error`. """
        self.ensure_one()
        self.retry_count += 1
        if self.state == 'failed':
            self.content = {
                **(self.content or {}),
                'status': {'code': ODOO_ERROR, 'description': "Odoo Error", 'details': [error]},
            }
        else:
            self._trigger_cron_when_due(cron_ref)

    def _trigger_next_window(self):
        """ A finished historic batch has the historic cron request the next window right away. """
        self.ensure_one()
        if self.kind == 'historic' and self.state in ('done', 'failed'):
            self.env.ref('l10n_pl_edi_batch.ir_cron_request_historic')._trigger()



    @api.model
    @ksef_cron('l10n_pl_edi_batch.ir_cron_download')
    def _cron_download(self):
        """ Download one missing part of the first due downloading batch, today batches first, and commit.
            Odoo runs the cron again right away while parts are left.
            A failed download counts a retry, and the batch is tried again once due; after the last retry, the
            batch fails with the download error. """
        ResCompany = self.env['res.company']
        due_batches = self._get_due_batches('downloading')
        for batch in due_batches:
            if not ResCompany._with_locked_records(batch, allow_raising=False):
                continue
            missing_parts = batch.part_ids.with_context(bin_size=True).filtered(lambda part: not part.decrypted_file)
            if error := self._try(missing_parts[:1].download):
                _logger.warning("KSeF batch %s: %s", batch.name, error)
                batch._count_retry(str(error), 'l10n_pl_edi_batch.ir_cron_download')
            if batch.state == 'downloaded':
                self.env.ref('l10n_pl_edi_batch.ir_cron_import')._trigger()
            batch._trigger_next_window()
            self._commit()
            downloading_batches = due_batches.filtered(lambda batch: batch.state == 'downloading')
            remaining_parts = downloading_batches.part_ids.with_context(bin_size=True).filtered(
                lambda part: not part.decrypted_file
            )
            self.env['ir.cron']._notify_progress(done=1, remaining=len(remaining_parts))
            return

    @api.model
    @ksef_cron('l10n_pl_edi_batch.ir_cron_import')
    def _cron_import(self):
        """ Import the bills of the first due downloaded batch, today batches first, and commit. Odoo runs the cron
            again right away while batches are left. Once a historic batch is done or failed, the historic cron
            requests the next window.
            No retries: the import is deterministic, and the standard import already catches the errors of each XML
            (see `_import_bill`). """
        ResCompany = self.env['res.company']
        due_batches = self._get_due_batches('downloaded')
        for batch in due_batches:
            if not ResCompany._with_locked_records(batch, allow_raising=False):
                continue
            batch.import_bills()
            batch._trigger_next_window()
            self._commit()
            remaining_batches = due_batches.filtered(lambda batch: batch.state == 'downloaded')
            self.env['ir.cron']._notify_progress(done=1, remaining=len(remaining_batches))
            return

    def action_trigger_check_status(self):
        """ Run the status cron now; it checks the requested batches that are due. """
        self.env.ref('l10n_pl_edi_batch.ir_cron_check_status').sudo()._trigger()

    def action_trigger_download(self):
        """ Run the download cron now; it downloads the parts of the batches that are due. """
        self.env.ref('l10n_pl_edi_batch.ir_cron_download').sudo()._trigger()

    def action_trigger_import(self):
        """ Run the import cron now; it imports the bills of the downloaded batches. """
        self.env.ref('l10n_pl_edi_batch.ir_cron_import').sudo()._trigger()


    def check_status(self):
        companies = self.mapped('company_id')
        if len(companies) != 1:
            raise ValueError("You must request KSeF status only for batches belonging to the same company")
        service = Service(companies[0])
        for record in self:
            data = service.download_batch_status(record.name)
            record.update(data)

    def import_bills(self):
        """ Join the parts into the ZIP, and turn each XML into a vendor bill, one commit per bill.
            The XMLs are never kept on the batch: if the run stops, the next one starts again from the parts,
            skipping the bills already created. The parts are deleted at the end: the batch is then done.
        """
        for record in self:
            if not record.part_ids:
                # Already imported, or nothing to import (0 invoices)
                continue
            # bin_size: only check the parts have a file, without loading it
            if not all(record.part_ids.with_context(bin_size=True).mapped('decrypted_file')):
                raise UserError(self.env._("All the parts of KSeF batch %s must be downloaded before importing it.", record.name))
            with tempfile.TemporaryFile(mode='w+b') as zip_stream:
                for part in record.part_ids.sorted('part_number'):
                    zip_stream.write(base64.b64decode(part.decrypted_file))
                zip_stream.seek(0)
                try:
                    zip_file = zipfile.ZipFile(zip_stream, 'r')
                except zipfile.BadZipFile as e:
                    # KSeF keeps the package until it expires: download the parts again
                    record.part_ids.decrypted_file = False
                    record.part_ids.invalidate_recordset(['decrypted_file'])
                    record._count_retry(self.env._("The KSeF batch ZIP is corrupt: %s", e), 'l10n_pl_edi_batch.ir_cron_download')
                    continue
                with zip_file:
                    for xml_name in zip_file.namelist():
                        if not xml_name.endswith('.xml'):
                            continue
                        record._import_bill(xml_name, zip_file.read(xml_name))
                        self._commit()
            record.part_ids.unlink()

    def _import_bill(self, xml_name, xml_content):
        """ Create the vendor bill of one KSeF XML and import it, unless a bill with its KSeF number exists.
            The standard import catches the errors of the XML: an unreadable one is only logged
            (`ir.attachment._decode_edi_xml`), a decoder error is posted in the bill's chatter
            (`account.move._extend_with_attachments`). Either way, the bill stays empty with its XML attached, and
            the next XML is imported. """
        self.ensure_one()
        AccountMove = self.env['account.move'].with_company(self.company_id)
        ksef_number = xml_name.removesuffix('.xml')
        if AccountMove.search_count([
            ('l10n_pl_edi_number', '=', ksef_number),
            ('company_id', '=', self.company_id.id),
            ('move_type', '=', 'in_invoice'),
        ], limit=1):
            return
        move = AccountMove.create([{'move_type': 'in_invoice'}])
        attachment = self.env['ir.attachment'].create({
            'name': xml_name,
            'mimetype': 'application/xml',
            'company_id': self.company_id.id,
            'res_model': move._name,
            'res_id': move.id,
            'raw': xml_content,
        })
        # Posting the attachment imports it (account.move._message_post_after_hook)
        move.message_post(body=self.env._("KSeF bill %s has been attached", xml_name), attachment_ids=attachment.ids)
        attachment.write({
            'description': self.env._('KSeF Received Bill XML'),
            'res_field': 'l10n_pl_edi_attachment_file',
        })
        move.write({
            'l10n_pl_edi_number': ksef_number,
            'l10n_pl_edi_status': 'fetched',
            'l10n_pl_edi_attachment_id': attachment.id,
        })
        move.invalidate_recordset(fnames=['l10n_pl_edi_attachment_id', 'l10n_pl_edi_attachment_file'])
