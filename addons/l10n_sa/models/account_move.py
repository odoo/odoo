# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from datetime import datetime
from pytz import timezone, utc

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_repr, format_datetime


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_sa_qr_code_str = fields.Char(string='Zatka QR Code', compute='_compute_qr_code_str')
    l10n_sa_confirmation_datetime = fields.Datetime(string='ZATCA Issue Date',
                                                    readonly=True,
                                                    copy=False,
                                                    help="""Date on which the invoice is generated as final document (after securing all internal approvals).""")

    @api.depends('country_code', 'move_type')
    def _compute_show_delivery_date(self):
        # EXTENDS 'account'
        super()._compute_show_delivery_date()
        for move in self:
            if move.country_code == 'SA':
                move.show_delivery_date = move.is_sale_document()

    def _l10n_sa_reset_confirmation_datetime(self):
        self.filtered(lambda m: m.country_code == 'SA').l10n_sa_confirmation_datetime = False

    @api.depends('amount_total_signed', 'amount_tax_signed', 'l10n_sa_confirmation_datetime', 'company_id', 'company_id.vat')
    def _compute_qr_code_str(self):
        """ Generate the qr code for Saudi e-invoicing. Specs are available at the following link at page 23
        https://zatca.gov.sa/ar/E-Invoicing/SystemsDevelopers/Documents/20210528_ZATCA_Electronic_Invoice_Security_Features_Implementation_Standards_vShared.pdf
        """
        def get_qr_encoding(tag, field):
            company_name_byte_array = field.encode()
            company_name_tag_encoding = tag.to_bytes(length=1, byteorder='big')
            company_name_length_encoding = len(company_name_byte_array).to_bytes(length=1, byteorder='big')
            return company_name_tag_encoding + company_name_length_encoding + company_name_byte_array

        for record in self:
            qr_code_str = ''
            if record.l10n_sa_confirmation_datetime and record.company_id.vat:
                seller_name_enc = get_qr_encoding(1, record.company_id.display_name)
                company_vat_enc = get_qr_encoding(2, record.company_id.vat)
                time_sa = fields.Datetime.context_timestamp(self.with_context(tz='Asia/Riyadh'), record.l10n_sa_confirmation_datetime)
                timestamp_enc = get_qr_encoding(3, time_sa.strftime(self._get_iso_format_asia_riyadh_date('T')))
                totals = record._get_l10n_sa_totals()
                invoice_total_enc = get_qr_encoding(4, float_repr(abs(totals['total_amount']), 2))
                total_vat_enc = get_qr_encoding(5, float_repr(abs(totals['total_tax']), 2))

                str_to_encode = seller_name_enc + company_vat_enc + timestamp_enc + invoice_total_enc + total_vat_enc
                qr_code_str = base64.b64encode(str_to_encode).decode()
            record.l10n_sa_qr_code_str = qr_code_str

    def _post(self, soft=True):
        res = super()._post(soft)
        for move in self:
            if move.country_code == 'SA' and move.is_sale_document():
                vals = {}
                if not move.l10n_sa_confirmation_datetime:
                    vals['l10n_sa_confirmation_datetime'] = self._get_normalized_l10n_sa_confirmation_datetime(move.invoice_date)
                if not move.delivery_date:
                    vals['delivery_date'] = move.invoice_date
                if vals:
                    move.write(vals)
        return res

    def get_l10n_sa_confirmation_datetime_sa_tz(self):
        self.ensure_one()
        return format_datetime(self.env, self.l10n_sa_confirmation_datetime, tz='Asia/Riyadh', dt_format='Y-MM-dd\nHH:mm:ss')

    def _get_iso_format_asia_riyadh_date(self, separator=' '):
        return f'%Y-%m-%d{separator}%H:%M:%S'

    def _get_l10n_sa_totals(self):
        self.ensure_one()
        return {
            'total_amount': self.amount_total_signed,
            'total_tax': self.amount_tax_signed,
        }

    def _get_normalized_l10n_sa_confirmation_datetime(self, invoice_date, invoice_time=None):
        """
            Makes sure that the l10n_sa_confirmation_datetime is not in the future because of different user timezones
            and how we store timezone unaware datetimes in the database.
            e.g. The date/time now is 1/1/2026 22:00:00 UTC+0, a user in Belgium (date/time 1/1/2026 23:00:00 UTC+1)
            sets the invoice date to the date now in Saudi Arabia (date/time 2/1/2026 01:00:00 UTC+3) because that's
            the date when the invoice was created to the Saudi Govt.
            A bug will arise because the date we store in the database will be 2/1/2026 22:00:00 (no tz) which is
            in the future and will cause ZATCA to reject the invoice.
        """
        sa_tz = timezone('Asia/Riyadh')
        now_sa = datetime.now(sa_tz)
        selected_date = fields.Date.from_string(invoice_date) if isinstance(invoice_date, str) else invoice_date
        if selected_date > now_sa.date():
            raise UserError(_("Please set the Invoice Date to be either less than or equal to today as per the Asia/Riyadh time zone, since ZATCA does not allow future-dated invoicing."))
        return min(now_sa, sa_tz.localize(datetime.combine(selected_date, invoice_time or now_sa.time()))).astimezone(utc).replace(tzinfo=None)

    def write(self, vals):
        result = super().write(vals)
        invoice_date = vals.get('invoice_date')
        if not invoice_date:
            return result
        for move in self.filtered('l10n_sa_confirmation_datetime'):
            sa_time = move.l10n_sa_confirmation_datetime.replace(tzinfo=utc).astimezone(timezone('Asia/Riyadh')).time()
            move.l10n_sa_confirmation_datetime = self._get_normalized_l10n_sa_confirmation_datetime(invoice_date, sa_time)
        return result

    def _l10n_sa_is_simplified(self):
        """
            Returns True if the customer is an individual, i.e: The invoice is B2C
        :return:
        """
        self.ensure_one()

        return (
            self.partner_id.commercial_partner_id.company_type == "person"
            if self.partner_id.commercial_partner_id
            else self.partner_id.company_type == "person"
        )
