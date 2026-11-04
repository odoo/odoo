import tempfile
import zipfile

from odoo import api, fields, models, modules
from odoo.exceptions import UserError
from odoo.osv.expression import OR

from odoo.addons.l10n_pl_edi_batch.tools.ksef_api_service import KsefApiServiceBatch as Service


STATUS_CODES = [
    ('100', 'In Progress'),
    ('200', 'Successful'),
    ('210', 'Expired'),
    ('415', 'Decryption Error'),
    ('420', 'Date Range Error'),
    ('500', 'Unknown Error'),
    ('550', 'Cancelled'),
]


class BatchDownload(models.Model):
    _name = 'l10n_pl_edi_batch.download'
    _description = "KSeF Batch Download"

    active = fields.Boolean()
    company_id = fields.Many2one(comodel_name='res.company', readonly=True, required=True)
    name = fields.Char("KSeF batch reference number", index=True, readonly=True, required=True)
    status = fields.Selection(selection=STATUS_CODES, readonly=True, required=True)
    error = fields.Char("KSeF batch download error", copy=False, readonly=True)
    content = fields.Json(readonly=True)

    # Dates and expiry
    date_from = fields.Datetime(readonly=True, required=True)
    date_to = fields.Datetime(readonly=True, required=True)
    date_expiry = fields.Datetime(readonly=True)
    is_expired = fields.Boolean(compute='_compute_is_expired', search='_search_expired')

    # Files
    part_ids = fields.One2many(comodel_name='l10n_pl_edi_batch.part', string='KSeF Batch parts', readonly=True, copy=False, inverse_name='batch_id')
    attachment_ids = fields.One2many(string='Downloaded KSeF XMLs', comodel_name='ir.attachment', inverse_name='res_id', domain=[('res_model', '=', 'l10n_pl_edi_batch.download')], readonly=True, copy=False)

    # Cryptographic info
    raw_symmetric_key = fields.Binary("Batch symmetric key", readonly=True, groups='base.group_system')
    encrypted_symmetric_key = fields.Binary("Batch encrypted symmetric key", readonly=True, groups='base.group_system')
    raw_iv = fields.Binary("Batch iv", readonly=True, groups='base.group_system')
    raw_symmetric_key_b64 = fields.Char("Symmetric Key (Base64)", readonly=True, compute='_compute_crypto_b64', groups='base.group_system')
    encrypted_symmetric_key_b64 = fields.Char("Encrypted Key (Base64)", readonly=True, compute='_compute_crypto_b64', groups='base.group_system')
    raw_iv_b64 = fields.Char("IV (Base64)", readonly=True, compute='_compute_crypto_b64', groups='base.group_system')

    _sql_constraints = [('unique_batch_name', 'UNIQUE(name)', 'The KSeF batch name must be unique')]

    @api.depends('raw_symmetric_key', 'encrypted_symmetric_key', 'raw_iv')
    def _compute_crypto_b64(self):
        for record in self:
            record.raw_symmetric_key_b64 = Service.b64(record.raw_symmetric_key)
            record.encrypted_symmetric_key_b64 = Service.b64(record.encrypted_symmetric_key)
            record.raw_iv_b64 = Service.b64(record.raw_iv)

    @api.model
    def _search_expired(self, operator, value):
        if operator not in ('=', '!='):
            raise NotImplementedError(self.env._("Operation not supported"))
        target_value = bool(value) if operator == '=' else not bool(value)
        now = fields.Datetime.now()
        if target_value:
            return [('date_expiry', '<', now)]
        return ['|', ('date_expiry', '>=', now), ('date_expiry', '=', False)]

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
        """Unlink expired KSeF batch download records and clean up associated attachments."""
        if expired_batches := self.sudo().with_context(active_test=False).search(OR([
            [('is_expired', '=', True)],
            [('active', '=', False)],
        ])):
            expired_batches.unlink()

    @api.model
    def _request(self, company, date_from, date_to):
        service = Service(company)
        encryption_data = service._create_encryption_data()
        batch_data = service.download_batch_request(date_from, date_to, encryption_data)
        return self.sudo().create({
            'active': True,
            'company_id': company.id,
            'status': '100',
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

    def unzip(self, commit=True):
        """ The parts are the slices of a single ZIP: join all of them, in order, then extract the XMLs on the batch. """
        self.ensure_one()
        if not self.part_ids or any(part.file_size == 0 for part in self.part_ids):
            raise UserError(self.env._("All the parts of KSeF batch %s must be downloaded before unzipping it.", self.name))
        sorted_parts = self.part_ids.sorted('part_number')
        existing_names = self.attachment_ids.mapped('name')
        Attachment = self.env['ir.attachment'].sudo()
        with tempfile.TemporaryFile(mode='w+b') as temp_zip_stream:
            for part in sorted_parts:
                temp_zip_stream.write(part.raw)
            temp_zip_stream.seek(0)
            with zipfile.ZipFile(temp_zip_stream, 'r') as zf:
                xml_names = [
                    name
                    for name in zf.namelist()
                    if '.json' not in name
                    and name not in existing_names
                ]
                for xml_name in xml_names:
                    with zf.open(xml_name) as xml_file:
                        content = xml_file.read()
                    Attachment.create({
                        'name': xml_name,
                        'mimetype': 'application/xml',
                        'company_id': self.company_id.id,
                        'res_model': self._name,
                        'res_id': self.id,
                        'raw': content,
                    })
                    if commit and not modules.module.current_test:
                        self.env.cr.commit()
        self.invalidate_recordset(fnames=['attachment_ids'])
        return self.attachment_ids

    def import_attachments(self, commit=True):
        for record in self:
            for attachment in record.attachment_ids:
                move = self.env['account.move'].with_company(record.company_id).create([{
                    'move_type': 'in_invoice',
                }])
                # Commit before and after the import, as 19.0 does instead of a savepoint (rollbackable_transaction)
                if not modules.module.current_test:
                    self.env.cr.commit()
                # Posting the attachment imports it (account.move._message_post_after_hook)
                move.message_post(body=self.env._("KSeF bill %s has been attached", attachment.name), attachment_ids=attachment.ids)
                attachment.write({
                    'company_id': record.company_id.id,
                    'description': self.env._('KSeF Received Bill XML'),
                    'res_model': move._name,
                    'res_field': 'l10n_pl_edi_attachment_file',
                    'res_id': move.id,
                })
                move.write({
                    'l10n_pl_edi_number': attachment.name.replace('.xml', ''),
                    'l10n_pl_edi_attachment_id': attachment.id,
                })
                move.invalidate_recordset(fnames=['l10n_pl_edi_attachment_id', 'l10n_pl_edi_attachment_file'])
                if not modules.module.current_test:
                    self.env.cr.commit()

            # Schedule for deletion through autovacuum
            record.active = False
