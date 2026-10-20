from odoo import api, fields, models, modules

from odoo.addons.l10n_pl_edi.tools.ksef_api_service import KsefApiService, u64


STATUS_CODES = [
    ('100', 'in_progress'),
    ('200', 'succesful'),
    ('210', 'expired'),
    ('415', 'error_decryption'),
    ('420', 'error_date_range'),
    ('500', 'error_unknown'),
    ('550', 'error_cancelled'),
]


class BatchDownload(models.Model):
    _name = "l10n_pl_edi_batch.download"
    _description = "KSeF Batch Download"

    company_id = fields.Many2one(comodel_name='res.company', readonly=True, required=True)
    name = fields.Char("KSeF batch reference number", index=True, readonly=True, required=True)

    date_from = fields.Datetime(readonly=True, required=True)
    date_to = fields.Datetime(readonly=True, required=True)
    date_expiry = fields.Datetime(readonly=True)
    is_expired = fields.Boolean(compute="_compute_is_expired", search="_search_expired")

    status = fields.Selection(selection=STATUS_CODES, readonly=True, required=True)
    content = fields.Json(readonly=True)
    error = fields.Char("KSeF batch download error", copy=False, readonly=True)

    raw_symmetric_key = fields.Binary("Batch symmetric key", readonly=True, groups='base.group_system')
    encrypted_symmetric_key = fields.Binary("Batch encrypted symmetric key", readonly=True, groups='base.group_system')
    raw_iv = fields.Binary("Batch iv", readonly=True, groups='base.group_system')

    part_ids = fields.One2many(
        comodel_name='l10n_pl_edi_batch.part',
        string='KSeF Batch parts',
        readonly=True,
        copy=False,
        inverse_name='batch_id',
    )
    attachment_ids = fields.One2many(
        string='Downloaded KSeF XMLs',
        comodel_name='ir.attachment',
        inverse_name='res_id',
        domain=[('res_model', '=', 'l10n_pl_edi_batch.download')],
        readonly=True,
        copy=False,
    )

    _sql_constraints = [('unique_batch_name', 'UNIQUE(name)', 'The KSeF batch name must be unique')]

    @api.model
    def _search_expired(self, operator, value):
        if operator not in ("=", "!="):
            raise NotImplementedError(self.env._("Operation not supported"))
        target_value = bool(value) if operator == "=" else not bool(value)
        now = fields.Datetime.now()
        if target_value:
            return [("date_expiry", "<", now)]
        return ["|", ("date_expiry", ">=", now), ("date_expiry", "=", False)]

    @api.depends("date_expiry")
    def _compute_is_expired(self):
        now = fields.Datetime.now()
        for record in self:
            record.is_expired = (record.date_expiry and record.date_expiry < now)

    @api.autovacuum
    def _gc_batch_downloads(self):
        """Unlink expired KSeF batch download records and clean up associated attachments."""
        if expired_batches := self.search([('is_expired', '=', True)]):
            expired_batches.unlink()

    @api.model
    def _request(self, company, date_from, date_to):
        service = KsefApiService(company)
        encryption_data = service._create_encryption_data()
        for record in self:
            batch_data = service.download_batch_request(date_from, date_to, encryption_data)
            return self.sudo().create({
                'company_id': company.id,
                'status': '100',
                'name': batch_data.get('referenceNumber', False),
                'date_from': fields.Datetime.to_string(date_from),
                'date_to': fields.Datetime.to_string(date_to),
                'raw_symmetric_key': u64(encryption_data['raw_symmetric_key']),
                'encrypted_symmetric_key': u64(encryption_data['encrypted_symmetric_key']),
                'raw_iv': u64(encryption_data['raw_iv']),
            }).with_env(self.env)

    def check_status(self):
        companies = self.mapped("company_id")
        if len(companies) != 1:
            raise ValueError("You must request KSeF status only for batches belonging to the same company")
        service = KsefApiService(companies[0])
        for record in self:
            data = service.download_batch_status(record.name)
            record.update(data)

    def import_attachments(self, commit=True):
        for record in self:
            for attachment in record.attachment_ids:
                move = self.env['account.move'].sudo().with_company(record.company_id).create([{
                    'move_type': 'in_invoice',
                }])
                move.message_post(body=self.env._("KSeF bill %s has been attached", attachment.name), attachment_ids=attachment.ids)
                attachment.write({
                    'company_id': record.company_id.id,
                    'description': self.env._('KSeF Received Bill XML'),
                    'res_id': move.id,
                    'res_model': move._name,
                    'res_field': 'l10n_pl_edi_attachment_file',
                })
                move.write({
                    'l10n_pl_edi_attachment_id': attachment.id,
                    'l10n_pl_edi_status': 'fetched',
                    'l10n_pl_edi_header': 'Fetched From KSeF',
                })
                move.invalidate_recordset(fnames=['l10n_pl_edi_attachment_id', 'l10n_pl_edi_attachment_file'])
            if not modules.module.current_test:
                self.env.cr.commit()
