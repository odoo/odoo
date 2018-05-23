# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields, _
from odoo.tools import pycompat, DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

import io
import zipfile
import base64
import hashlib

from datetime import datetime


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_pos_cert_sequence_id = fields.Many2one('ir.sequence')

    @api.model
    def create(self, vals):
        company = super(ResCompany, self).create(vals)
        #when creating a new french company, create the securisation sequence as well
        if company._is_accounting_unalterable():
            sequence_fields = ['l10n_fr_pos_cert_sequence_id']
            company._create_secure_sequence(sequence_fields)
        return company

    @api.multi
    def write(self, vals):
        res = super(ResCompany, self).write(vals)
        #if country changed to fr, create the securisation sequence
        for company in self:
            if company._is_accounting_unalterable():
                sequence_fields = ['l10n_fr_pos_cert_sequence_id']
                company._create_secure_sequence(sequence_fields)

        # Create an archive containing all the POS sales data to ensure the original data
        # remain unchanged/untouched/unmodified. It's a legal requirements in the French law.
        if vals.get('fiscalyear_lock_date'):
            self._l10n_fr_create_archive_attachment(vals['fiscalyear_lock_date'])

        return res

    @api.model
    def _l10n_fr_compute_csv_archive_content(self, records_vals, fields):
        '''Compute the content of a CSV in memory using BytesIO.
        This CSV contains the technical fields names are headers and is comma separated.

        :param records_vals:    A list of dictionary, one for each record.
        :param fields:          A list of string containing the fields names to export.
        :return:                The bytes representing the content of the CSV.
        '''
        def replace_delimiter(value, delimiter):
            # Avoid having the delimiter in a value
            if value and isinstance(value, pycompat.string_types):
                return value.replace(delimiter, '-')
            return value

        delimiter = ';'
        output = io.BytesIO()
        writer = pycompat.csv_writer(output, delimiter=delimiter)

        writer.writerow(fields)
        for vals in records_vals:
            row = [replace_delimiter(vals[f], delimiter) for f in fields]
            writer.writerow(row)

        csv_content = output.getvalue()
        output.close()
        return csv_content

    @api.multi
    def _l10n_fr_compute_amls_csv_archive_content(self, date):
        '''Compute the filename and the CSV content of the journal entries linked to the POS journal.

        :return: filename, csv_content
        '''
        self.ensure_one()

        # Filename
        filename = 'archive_journal_items.csv'

        # Mapping headers -> fields
        fields = ['id', 'ref', 'create_date', 'date', 'debit', 'credit', 'balance',
                  'debit_cash_basis', 'credit_cash_basis', 'balance_cash_basis',
                  'amount_currency', 'currency_name', 'tax_name', 'partner', 'product_name',
                  'quantity', 'unit_of_measure', 'account', 'reconciled', 'reconciliation',
                  'hash_sequence', 'hash']

        # Query
        query = '''
            SELECT
                line.id AS id,
                line.ref AS ref,
                line.create_date AS create_date,
                line.date AS date,
                line.debit AS debit,
                line.credit AS credit,
                line.balance AS balance,
                line.debit_cash_basis AS debit_cash_basis,
                line.credit_cash_basis AS credit_cash_basis,
                line.balance_cash_basis AS balance_cash_basis,
                line.amount_currency AS amount_currency,
                move.l10n_fr_secure_sequence_number AS hash_sequence,
                move.l10n_fr_hash AS hash,
                currency.name AS currency_name,
                tax.name AS tax_name,
                partner.name AS partner,
                template.name AS product_name,
                line.quantity AS quantity,
                uom.name AS unit_of_measure,
                account.name AS account,
                line.reconciled AS reconciled,
                rec.name AS reconciliation
            FROM account_move_line line
            LEFT JOIN account_move move ON move.id = line.move_id
            LEFT JOIN account_journal j ON j.id = line.journal_id
            LEFT JOIN res_currency currency ON currency.id = line.currency_id
            LEFT JOIN account_tax tax ON tax.id = line.tax_line_id
            LEFT JOIN account_account account ON account.id = line.account_id
            LEFT JOIN uom_uom uom ON uom.id = line.product_uom_id
            LEFT JOIN product_product product ON product.id = line.product_id
            LEFT JOIN product_template template ON template.id = product.product_tmpl_id
            LEFT JOIN account_full_reconcile rec ON rec.id = line.full_reconcile_id
            LEFT JOIN res_partner partner ON partner.id = line.partner_id
            WHERE move.state = 'posted'
                AND line.date <= %s
                AND line.company_id = %s
                AND j.type = 'sale'
            ORDER BY line.id
        '''
        params = [date, self.id]

        self._cr.execute(query, params)
        return filename, self._l10n_fr_compute_csv_archive_content(self._cr.dictfetchall(), fields)

    @api.multi
    def _l10n_fr_compute_pos_lines_csv_archive_content(self, date):
        '''Compute the filename and the CSV content of the POS order lines.

        :return: filename, csv_content
        '''
        self.ensure_one()

        # Filename
        filename = 'archive_post_order_lines.csv'

        # Mapping headers -> fields
        fields = ['id', 'name', 'create_date', 'product_name', 'price_unit', 'quantity', 'discount',
                  'hash_sequence', 'hash', 'order_name']

        # Query
        query = '''
            SELECT
                line.id AS id,
                line.name AS name,
                line.create_date AS create_date,
                template.name AS product_name,
                line.price_unit AS price_unit,
                line.qty AS quantity,
                line.discount AS discount,
                ord.l10n_fr_secure_sequence_number AS hash_sequence,
                ord.l10n_fr_hash AS hash,
                ord.name AS order_name
            FROM pos_order_line line
            LEFT JOIN pos_order ord ON ord.id = line.order_id
            LEFT JOIN product_product product ON product.id = line.product_id
            LEFT JOIN product_template template ON template.id = product.product_tmpl_id
            WHERE ord.state in ('paid', 'done', 'invoiced')
            AND line.create_date <= %s
            AND line.company_id = %s
            ORDER BY line.id
        '''
        dt = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT).replace(hour=23, minute=59, second=59)
        date = dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        params = [date, self.id]

        self._cr.execute(query, params)
        return filename, self._l10n_fr_compute_csv_archive_content(self._cr.dictfetchall(), fields)

    @api.multi
    def _l10n_fr_compute_sales_closing_csv_archive_content(self, date):
        '''Compute the filename and the CSV content of the sales closings records.

        :return: filename, csv_content
        '''
        self.ensure_one()

        # Filename
        filename = 'archive_account_sale_closing.csv'

        # Mapping headers -> fields
        fields = ['id', 'name', 'create_date', 'date_start', 'date_close', 'frequency', 'total_interval',
                  'cumulative_total', 'sequence_number', 'last_move_name', 'last_move_hash', 'currency_name']

        # Query
        query = '''
            SELECT
                closing.id AS id,
                closing.name AS name,
                closing.create_date AS create_date,
                closing.date_closing_start AS date_start,
                closing.date_closing_stop AS date_close,
                closing.frequency AS frequency,
                closing.total_interval AS total_interval,
                closing.cumulative_total AS cumulative_total,
                closing.sequence_number AS sequence_number,
                move.name AS last_move_name,
                closing.last_move_hash AS last_move_hash,
                currency.name AS currency_name
            FROM account_sale_closing closing
            LEFT JOIN account_move move ON move.id = closing.last_move_id
            LEFT JOIN res_currency currency ON currency.id = closing.currency_id
            WHERE closing.create_date <= %s
            AND closing.company_id = %s
            ORDER BY closing.id
        '''
        params = [date, self.id]

        self._cr.execute(query, params)
        return filename, self._l10n_fr_compute_csv_archive_content(self._cr.dictfetchall(), fields)

    @api.model
    def _l10n_fr_compute_hash(self, hashable_bytes):
        ''' Hash the archive contents passed as parameter using SHA1.
        :param hashable_bytes:  A list of byte-encoded chains to hash.
        :return:                A hash of the ZIP content.
        '''
        hasher = hashlib.sha1()
        for bytes in hashable_bytes:
            hasher.update(bytes)
        return hasher.hexdigest()

    @api.multi
    def _l10n_fr_create_archive_attachment(self, date):
        ''' This method creates missing archives according to the french law.
        This is a way to ensure the POS data are not altered.
        Such archives must be generated at least once a year.

        :param date: The date until which the archive will be generated.
        '''
        for company in self:
            output = io.BytesIO()

            filename1, content1 = company._l10n_fr_compute_amls_csv_archive_content(date)
            filename2, content2 = company._l10n_fr_compute_pos_lines_csv_archive_content(date)
            filename3, content3 = company._l10n_fr_compute_sales_closing_csv_archive_content(date)

            zip_file = zipfile.ZipFile(output, 'a', compression=zipfile.ZIP_DEFLATED)
            zip_file.writestr(filename1, content1)
            zip_file.writestr(filename2, content2)
            zip_file.writestr(filename3, content3)
            zip_file.close()

            output.seek(0)
            zip_content = output.getvalue()
            output.close()

            # Compute the hash using contents instead of hashing the whole zip because it doesn't ensure
            # the same hash for the same content.
            hashable_bytes = [content1, content2, content3]

            now = datetime.now()

            zip_filename = '%s_archive-%s_%s.zip' % (
                company.name,
                now.strftime('%y%m%d_%H%M%S'),
                self._l10n_fr_compute_hash(hashable_bytes)
            )

            attachment = self.env['ir.attachment'].create({
                'name': zip_filename,
                'datas_fname': zip_filename,
                'datas': base64.encodestring(zip_content),
                'res_model': 'res.company',
                'res_id': company.id,
                'type': 'binary',
            })

            message = _('An archive of your sales data has been generated.')

            company.partner_id.message_post(body=message, attachment_ids=[attachment.id])
