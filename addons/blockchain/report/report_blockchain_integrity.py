from odoo import models, _, api, fields
from odoo.tools import format_date


class ReportBlockchainIntegrity(models.AbstractModel):
    _name = 'report.blockchain.report_blockchain_integrity'
    _description = 'Get blockchain integrity result as a PDF file.'

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        data.update(self._check_blockchain_integrity())
        return {
            'doc_ids': docids,
            'doc_model': self.env['res.company'],
            'data': data,
            'docs': self.env['res.company'].browse(self.env.company.id),
        }

    @api.model
    def _check_blockchain_integrity(self, records=None, date_field=None, must_check=True):
        """This method must be extended by the inherit report to fill in the correct arguments."""
        assert date_field, 'The date_field argument must be set.'
        if not must_check:
            return {
                'status': 'not_checked',
                'msg': _('The integrity check has not been performed.'),
            }

        records = records.filtered(lambda r: r.blockchain_inalterable_hash)
        if not records:
            return {
                'status': 'no_record',
                'msg': _("There isn't any record flagged for data inalterability."),
            }

        records = records.sorted("blockchain_secure_sequence_number")
        corrupted_record = None
        previous_hash = ''
        current_hash_version = 1
        max_hash_version = records._get_blockchain_max_version()
        for record in records:
            computed_hash = record.with_context(hash_version=current_hash_version)._get_blockchain_record_hash_string(previous_hash=previous_hash)
            while record.blockchain_inalterable_hash != computed_hash and current_hash_version < max_hash_version:
                current_hash_version += 1
                computed_hash = record.with_context(hash_version=current_hash_version)._get_blockchain_record_hash_string(previous_hash=previous_hash)
            if record.blockchain_inalterable_hash != computed_hash:
                corrupted_record = record
                break
            previous_hash = record.blockchain_inalterable_hash
        records.invalidate_recordset()  # See dcffa8997a1c94309ecab2bf7996b0391b46910c

        if corrupted_record is not None:
            return {
                'status': 'corrupted',
                'msg': _('Corrupted data on record %s with id %s.', corrupted_record.name, corrupted_record.id),
            }

        return {
            'status': 'verified',
            'msg': _('Entries are hashed from %s (%s)', records[0].name, format_date(self.env, fields.Date.to_string(records[0][date_field]))),
            'first_name': records[0]['name'],
            'first_hash': records[0]['blockchain_inalterable_hash'],
            'first_date': format_date(self.env, fields.Date.to_string(records[0][date_field])),
            'last_name': records[-1]['name'],
            'last_hash': records[-1]['blockchain_inalterable_hash'],
            'last_date': format_date(self.env, fields.Date.to_string(records[-1][date_field])),
        }
