import base64
import tempfile
import zipfile
from datetime import timedelta, timezone

from dateutil.parser import parse

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_pl_edi_batch.tools.ksef_api_service import KsefApiServiceBatch as Service


# KSeF export status codes: 100 while KSeF builds the ZIP, 200 once it's ready, anything else is an error
KSEF_IN_PROGRESS = 100
KSEF_READY = 200
# Our own errors (failed download, corrupt ZIP), written like KSeF's; KSeF never sends it
ODOO_ERROR = 999

STATES = [
    ('requested', 'Requested'),
    ('downloading', 'Downloading'),
    ('downloaded', 'Downloaded'),
    ('done', 'Done'),
    ('failed', 'Failed'),
]

# Retries allowed for each step (polling at 100, downloading the parts); one more failure fails the batch
MAX_RETRIES = 9


class BatchDownload(models.Model):
    _name = 'l10n_pl_edi_batch.download'
    _description = "KSeF Batch Download"

    company_id = fields.Many2one(comodel_name='res.company', readonly=True, required=True)
    name = fields.Char("KSeF batch reference number", index=True, readonly=True, required=True)
    error = fields.Char("KSeF batch download error", compute='_compute_error')
    content = fields.Json(readonly=True)
    kind = fields.Selection(
        selection=[('today', 'Today'), ('historic', 'Historic')],
        compute='_compute_kind',
        search='_search_kind',
    )
    retry_count = fields.Integer(default=0, readonly=True, copy=False)
    state = fields.Selection(selection=STATES, compute='_compute_state', search='_search_state')

    date_from = fields.Datetime(readonly=True, required=True)
    date_to = fields.Datetime(readonly=True, required=True)
    date_expiry = fields.Datetime(compute='_compute_date_expiry')
    is_expired = fields.Boolean(compute='_compute_is_expired', search='_search_expired')

    part_ids = fields.One2many(comodel_name='l10n_pl_edi_batch.part', string='KSeF Batch parts', readonly=True, copy=False, inverse_name='batch_id')

    raw_symmetric_key = fields.Binary("Batch symmetric key", readonly=True, groups='base.group_system')
    encrypted_symmetric_key = fields.Binary("Batch encrypted symmetric key", readonly=True, groups='base.group_system')
    raw_iv = fields.Binary("Batch iv", readonly=True, groups='base.group_system')

    _sql_constraints = [('unique_batch_name', 'UNIQUE(name)', 'The KSeF batch name must be unique')]

    def _get_ksef_status_code(self):
        """ The status code of the saved KSeF answer; no answer saved yet means the batch was just requested. """
        self.ensure_one()
        return (self.content or {}).get('status', {}).get('code') or KSEF_IN_PROGRESS

    @api.depends('content')
    def _compute_error(self):
        for record in self:
            code = record._get_ksef_status_code()
            if code in (KSEF_IN_PROGRESS, KSEF_READY):
                record.error = False
                continue
            ksef_status = (record.content or {}).get('status', {})
            description = ksef_status.get('description')
            lines = [f"{code}: {description}" if description else str(code)] + (ksef_status.get('details') or [])
            record.error = '\n'.join(lines)

    def _set_odoo_error(self, message):
        """ Our own errors go where KSeF puts its own: in the saved answer's status, with code 999. """
        for record in self:
            record.content = {
                **(record.content or {}),
                'status': {'code': ODOO_ERROR, 'description': "Odoo Error", 'details': [message]},
            }

    @api.depends('date_to', 'create_date')
    def _compute_kind(self):
        for record in self:
            # A today batch ends when it's requested; a historic one ends at least a day before
            create_date = record.create_date or fields.Datetime.now()
            if record.date_to and record.date_to <= create_date - timedelta(hours=24):
                record.kind = 'historic'
            else:
                record.kind = 'today'

    def _search_kind(self, operator, value):
        if operator not in ('=', '!=', 'in', 'not in'):
            raise NotImplementedError(self.env._("Operation not supported"))
        values = value if isinstance(value, (list, tuple)) else [value]
        batches = self.search([]).filtered(lambda batch: batch.kind in values)
        if operator in ('=', 'in'):
            return [('id', 'in', batches.ids)]
        return [('id', 'not in', batches.ids)]

    @api.depends('content', 'retry_count', 'part_ids.decrypted_file')
    def _compute_state(self):
        for record in self:
            code = record._get_ksef_status_code()
            # bin_size: only check the parts have a file, without loading it
            parts_missing = not all(record.part_ids.with_context(bin_size=True).mapped('decrypted_file'))
            if (
                code not in (KSEF_IN_PROGRESS, KSEF_READY)
                or record.retry_count > MAX_RETRIES
                # Once all the parts are downloaded, we don't need KSeF any more: expiry doesn't matter
                or (record.is_expired and parts_missing)
            ):
                record.state = 'failed'
            elif code == KSEF_IN_PROGRESS:
                record.state = 'requested'
            elif parts_missing:
                record.state = 'downloading'
            elif record.part_ids:
                record.state = 'downloaded'
            else:
                # The parts are deleted once imported; a batch with 0 invoices has none
                record.state = 'done'

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

    @api.depends('date_expiry')
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_expired = (record.date_expiry and record.date_expiry < now)

    def unlink(self):
        # Unlink the parts through the ORM, so that their attachments are removed too
        self.part_ids.unlink()
        return super().unlink()

    @api.autovacuum
    def _gc_batch_downloads(self):
        """ Delete the finished batches (done or failed), with their parts and XMLs. """
        # TODO: XXX step 4 of IMPLEMENT.md: only those finished more than 30 days ago
        if finished_batches := self.sudo().search([('state', 'in', ('done', 'failed'))]):
            finished_batches.unlink()

    @api.model
    def _request(self, company, date_from, date_to):
        service = Service(company)
        encryption_data = service._create_encryption_data()
        batch_data = service.download_batch_request(date_from, date_to, encryption_data)
        return self.sudo().create({
            'company_id': company.id,
            'name': batch_data.get('referenceNumber', False),
            'date_from': fields.Datetime.to_string(date_from),
            'date_to': fields.Datetime.to_string(date_to),
            # Binary fields are written base64-encoded, which is what encryption_data already holds
            'raw_symmetric_key': encryption_data['raw_symmetric_key'],
            'encrypted_symmetric_key': encryption_data['encrypted_symmetric_key'],
            'raw_iv': encryption_data['raw_iv'],
        }).with_env(self.env)

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
        AccountMove = self.env['account.move']
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
                    record._set_odoo_error(self.env._("The KSeF batch ZIP is corrupt: %s", e))
                    continue
                with zip_file:
                    for xml_name in zip_file.namelist():
                        if not xml_name.endswith('.xml'):
                            continue
                        record._import_bill(xml_name, zip_file.read(xml_name))
                        if AccountMove._can_commit():
                            self.env.cr.commit()
            record.part_ids.unlink()

    def _import_bill(self, xml_name, xml_content):
        """ Create the vendor bill of one KSeF XML and import it, unless a bill with its KSeF number exists. """
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
            'l10n_pl_edi_attachment_id': attachment.id,
        })
        move.invalidate_recordset(fnames=['l10n_pl_edi_attachment_id', 'l10n_pl_edi_attachment_file'])
