# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from zoneinfo import ZoneInfo

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_datetime


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move', 'zatca.mixin']

    def _get_name_invoice_report(self):
        # EXTENDS account
        self.ensure_one()
        if self.company_id.country_code == 'SA':
            return 'l10n_sa.l10n_sa_report_invoice_document'
        return super()._get_name_invoice_report()

    def _l10n_gcc_get_invoice_title(self):
        # EXTENDS l10n_gcc_invoice
        self.ensure_one()
        if self.company_id.country_code != "SA":
            return super()._l10n_gcc_get_invoice_title()

        if self._l10n_sa_is_simplified():
            return self.env._("Simplified Tax Invoice")

        return self.env._("Tax Invoice")

    def _l10n_sa_is_phase_1_applicable(self):
        # EXTENDS zatca_mixin
        return super()._l10n_sa_is_phase_1_applicable() and self.state == 'posted'

    @api.depends('country_code', 'move_type')
    def _compute_show_delivery_date(self):
        # EXTENDS 'account'
        super()._compute_show_delivery_date()
        for move in self:
            if move.country_code == 'SA':
                move.show_delivery_date = move.is_sale_document()

    @api.depends('move_type', 'debit_origin_id')
    def _compute_show_l10n_sa_reason(self):
        # EXTENDS zatca_mixin
        for record in self:
            record.l10n_sa_show_reason = record.country_code == 'SA' and (record.move_type == 'out_refund' or (record.move_type == 'out_invoice' and record.debit_origin_id))

    def _post(self, soft=True):
        res = super()._post(soft)
        for move in self:
            if move.country_code == 'SA' and move.is_sale_document():
                vals = {}
                if not move.l10n_sa_confirmation_datetime:
                    vals['l10n_sa_confirmation_datetime'] = self._get_normalized_l10n_sa_confirmation_datetime(move.invoice_date)
                if not move.delivery_date:
                    vals['delivery_date'] = move.invoice_date
                move.write(vals)
        return res

    def get_l10n_sa_confirmation_datetime_sa_tz(self):
        self.ensure_one()
        return format_datetime(self.env, self.l10n_sa_confirmation_datetime, tz='Asia/Riyadh', dt_format='Y-MM-dd\nHH:mm:ss')

    def _get_l10n_sa_totals(self):
        self.ensure_one()
        return {
            'total_amount': self.amount_total_signed,
            'total_tax': self.amount_tax_signed,
        }

    def _l10n_sa_is_legal(self):
        # Check if the document is legal in Saudi
        self.ensure_one()
        return self.company_id.country_id.code == 'SA' and self.state == 'posted' and self.l10n_sa_qr_code_str

    def _get_normalized_l10n_sa_confirmation_datetime(self, invoice_date, invoice_time=None):
        """
            Ensures the confirmation datetime does not exceed the current time in Asia/Riyadh to prevent ZATCA rejections.
        """
        sa_tz = ZoneInfo('Asia/Riyadh')
        now_sa = datetime.now(sa_tz)
        selected_date = fields.Date.from_string(invoice_date) if isinstance(invoice_date, str) else invoice_date
        if selected_date > now_sa.date():
            raise UserError(_("Please set the Invoice Date to be either less than or equal to today as per the Asia/Riyadh time zone, since ZATCA does not allow future-dated invoicing."))
        return min(now_sa, datetime.combine(selected_date, invoice_time or now_sa.time(), tzinfo=sa_tz)).astimezone(ZoneInfo('UTC')).replace(tzinfo=None)

    def write(self, vals):
        result = super().write(vals)
        invoice_date = vals.get('invoice_date')
        if not invoice_date:
            return result
        for move in self.filtered('l10n_sa_confirmation_datetime'):
            sa_time = move.l10n_sa_confirmation_datetime.replace(tzinfo=ZoneInfo('UTC')).astimezone(ZoneInfo('Asia/Riyadh')).time()
            move.l10n_sa_confirmation_datetime = self._get_normalized_l10n_sa_confirmation_datetime(invoice_date, sa_time)
        return result
