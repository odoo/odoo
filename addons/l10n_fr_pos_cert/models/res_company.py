# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api, fields, _
from odoo.tools import pycompat, DEFAULT_SERVER_DATETIME_FORMAT

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
            self._l10n_fr_create_archive_attachment()

        return res

    @api.model
    def _l10n_fr_compute_csv_archive_content(self, records_vals, fields):
        '''Compute the content of a CSV in memory using BytesIO.
        This CSV contains the technical fields names are headers and is comma separated.

        :param records_vals:    A list of dictionary, one for each record.
        :param fields:          A list of string containing the fields names to export.
        :return:                The bytes representing the content of the CSV.
        '''
        output = io.BytesIO()

        writer = pycompat.csv_writer(output, delimiter=',')

        writer.writerow(fields)
        for vals in records_vals:
            row = [isinstance(vals[f], unicode) and vals[f].encode('utf-8') or vals[f] for f in fields]
            writer.writerow(row)

        csv_content = output.getvalue()
        output.close()
        return csv_content

    @api.multi
    def _l10n_fr_compute_amls_csv_archive_content(self):
        '''Compute the filename and the CSV content of the journal entries linked to the POS journal.

        :return: filename, csv_content
        '''
        self.ensure_one()

        # Filename
        filename = 'archive_journal_items.csv'

        # Fields
        fields = ['id', 'name', 'quantity', 'product_uom_id', 'product_id', 'debit', 'credit', 'balance',
                  'debit_cash_basis', 'credit_cash_basis', 'balance_cash_basis', 'amount_currency',
                  'company_currency_id', 'currency_id', 'amount_residual', 'amount_residual_currency',
                  'tax_base_amount', 'account_id', 'move_id', 'ref', 'payment_id', 'statement_line_id',
                  'statement_id', 'reconciled', 'full_reconcile_id', 'date_maturity', 'date', 'tax_line_id',
                  'analytic_account_id', 'partner_id', 'user_type_id', 'tax_exigible', 'create_date']

        # Query
        select = 'SELECT %s ' % ', '.join('line.%s AS %s' % (f, f) for f in fields)
        query = """
            FROM account_move_line line
            LEFT JOIN account_move move ON move.id = line.move_id
            WHERE move.state = 'posted'
            AND line.date <= %s
            AND line.company_id = %s
            AND line.journal_id = %s
            ORDER BY line.id
        """
        params = [self.fiscalyear_lock_date, self.id, self.env.ref('point_of_sale.pos_sale_journal').id]
        self._cr.execute(select + query, params)
        return filename, self._l10n_fr_compute_csv_archive_content(self._cr.dictfetchall(), fields)

    @api.multi
    def _l10n_fr_compute_pos_lines_csv_archive_content(self):
        '''Compute the filename and the CSV content of the POS order lines.

        :return: filename, csv_content
        '''
        self.ensure_one()

        # Filename
        filename = 'archive_post_order_lines.csv'

        # Fields
        fields = ['id', 'name', 'notice', 'product_id', 'price_unit', 'qty', 'discount', 'order_id', 'create_date']

        # Query
        select = 'SELECT %s ' % ', '.join('line.%s AS %s' % (f, f) for f in fields)
        query = """
            FROM pos_order_line line
            LEFT JOIN pos_order ord ON ord.id = line.order_id
            WHERE ord.state in ('paid', 'done', 'invoiced')
            AND line.create_date <= %s
            AND line.company_id = %s
            ORDER BY line.id
        """
        params = [self.fiscalyear_lock_date, self.id]
        self._cr.execute(select + query, params)
        return filename, self._l10n_fr_compute_csv_archive_content(self._cr.dictfetchall(), fields)

    @api.multi
    def _l10n_fr_compute_sales_closing_csv_archive_content(self):
        '''Compute the filename and the CSV content of the sales closings records.

        :return: filename, csv_content
        '''
        self.ensure_one()

        # Filename
        filename = 'archive_account_sale_closing.csv'

        # Fields
        fields = ['id', 'name', 'date_closing_stop', 'date_closing_start', 'frequency', 'total_interval',
                  'cumulative_total', 'sequence_number', 'last_move_id', 'last_move_hash', 'currency_id', 'create_date']

        # Query
        select = 'SELECT %s ' % ', '.join('closing.%s AS %s' % (f, f) for f in fields)
        query = """
            FROM account_sale_closing closing
            WHERE closing.create_date <= %s
            AND closing.company_id = %s
            ORDER BY closing.id
        """
        params = [self.fiscalyear_lock_date, self.id]
        self._cr.execute(select + query, params)
        return filename, self._l10n_fr_compute_csv_archive_content(self._cr.dictfetchall(), fields)

    @api.model
    def _l10n_fr_compute_hash(self, zip_content):
        '''Hash the content passed as parameter using SHA1.

        :param zip_content: The content of the archive ZIP in bytes.
        :return: A hash of the ZIP content.
        '''
        hasher = hashlib.sha1(zip_content)
        return hasher.hexdigest()

    @api.multi
    def _l10n_fr_create_archive_attachment(self):
        '''Generate an attachement containing a ZIP archive.
        Itself contains some CSV files to ensure the POS sales data integrity.
        '''
        for company in self:
            output = io.BytesIO()

            zip_file = zipfile.ZipFile(output, 'a', compression=zipfile.ZIP_DEFLATED)
            zip_file.writestr(*company._l10n_fr_compute_amls_csv_archive_content())
            zip_file.writestr(*company._l10n_fr_compute_pos_lines_csv_archive_content())
            zip_file.writestr(*company._l10n_fr_compute_sales_closing_csv_archive_content())
            zip_file.close()

            output.seek(0)
            zip_content = output.getvalue()
            output.close()

            now = datetime.now()

            zip_filename = '%s_archive-%s_%s.zip' % (
                company.name,
                now.strftime('%y%m%d_%H%M%S'),
                self._l10n_fr_compute_hash(zip_content)
            )
            attachment = self.env['ir.attachment'].create({
                'name': zip_filename,
                'datas_fname': zip_filename,
                'datas': base64.encodestring(zip_content),
                'res_model': 'res.company',
                'res_id': company.id,
                'type': 'binary',
            })

            message = _('Point of Sale data archived:')
            message += '<ul><li>%s: %s</li></ul>' % (_('Date'), now.strftime(DEFAULT_SERVER_DATETIME_FORMAT))

            company.partner_id.message_post(
                body=message, subtype='l10n_fr_pos_cert.archive_posted', attachment_ids = [attachment.id])
