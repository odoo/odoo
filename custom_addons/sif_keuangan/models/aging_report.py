# -*- coding: utf-8 -*-
import datetime
from odoo import api, fields, models, _

class SifAgingReportLine(models.TransientModel):
    _name = 'sif.aging.report.line'
    _description = 'Detail Baris Laporan Umur Utang Dagang'

    vendor_id = fields.Many2one('sif.vendor', string='Rekanan / Vendor')
    vendor_name = fields.Char(string='Rekanan / Partner')
    ppl_name = fields.Char(string='No PPL / Faktur')
    invoice_date = fields.Date(string='Invoice Date')
    due_date = fields.Date(string='Tanggal Jatuh Tempo')
    overdue_days = fields.Integer(string='Umur (Hari)')

    current_amount = fields.Monetary(string='At Date')
    days_1_30 = fields.Monetary(string='1-30')
    days_31_60 = fields.Monetary(string='31-60')
    days_61_90 = fields.Monetary(string='61-90')
    days_91_120 = fields.Monetary(string='91-120')
    days_older = fields.Monetary(string='Older')

    total_amount = fields.Monetary(string='Total')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)


class SifAgedPayableEngine(models.AbstractModel):
    _name = 'sif.aged.payable'
    _description = 'Engine & Logic Aged Payable (Laporan Aging Hutang)'

    @api.model
    def _format_rupiah(self, amount):
        if amount is None or abs(amount) < 0.001:
            return "0.00"
        val = float(amount)
        prefix = "-Rp " if val < -0.001 else ""
        abs_val = abs(val)
        parts = f"{abs_val:,.2f}".split(".")
        int_part = parts[0].replace(",", ".")
        dec_part = parts[1]
        return f"{prefix}{int_part},{dec_part}"

    @api.model
    def get_aged_payable_data(self, filters=None):
        if not filters:
            filters = {}

        as_of_str = filters.get('as_of_date') or fields.Date.today().strftime('%Y-%m-%d')
        as_of_dt = fields.Date.to_date(as_of_str)

        based_on = filters.get('based_on') or 'due_date'
        period_days = int(filters.get('period_days') or 30)
        target_move = filters.get('target_move') or 'posted'
        partner_id = int(filters.get('partner_id')) if filters.get('partner_id') else False
        search_query = (filters.get('search') or '').strip().lower()

        domain = [('payment_term', '=', 'jatuh_tempo')]
        if target_move == 'posted':
            domain.append(('state', 'in', ['approved', 'paid', 'done']))
        else:
            domain.append(('state', 'in', ['draft', 'submitted', 'verified', 'approved', 'paid', 'done']))

        if partner_id:
            domain.append(('vendor_id', '=', partner_id))

        ppls = self.env['sifnext.ppl'].search(domain, order='vendor_id, request_date asc')

        unposted_count = self.env['sifnext.ppl'].search_count([
            ('payment_term', '=', 'jatuh_tempo'),
            ('state', 'in', ['draft', 'submitted', 'verified'])
        ])

        all_vendors = self.env['sif.vendor'].search([], order='name asc')
        vendors_list = [{'id': v.id, 'name': v.name} for v in all_vendors]

        interval = period_days

        grand_totals = {
            'current': 0.0,
            'b1': 0.0,
            'b2': 0.0,
            'b3': 0.0,
            'b4': 0.0,
            'older': 0.0,
            'total': 0.0,
        }

        vendors_dict = {}

        for ppl in ppls:
            v_id = ppl.vendor_id.id if ppl.vendor_id else 0
            v_name = ppl.vendor_id.name if ppl.vendor_id else 'Tanpa Rekanan'

            if search_query:
                if search_query not in v_name.lower() and search_query not in (ppl.name or '').lower() and search_query not in (ppl.title or '').lower():
                    continue

            due_date_val = ppl.due_date or ppl.request_date
            baseline_date = due_date_val if based_on == 'due_date' else ppl.request_date

            days = (as_of_dt - baseline_date).days if baseline_date else 0
            amt = ppl.total_amount

            c_amt = amt if days <= 0 else 0.0
            b1_amt = amt if 1 <= days <= interval else 0.0
            b2_amt = amt if interval < days <= interval * 2 else 0.0
            b3_amt = amt if interval * 2 < days <= interval * 3 else 0.0
            b4_amt = amt if interval * 3 < days <= interval * 4 else 0.0
            older_amt = amt if days > interval * 4 else 0.0

            if v_id not in vendors_dict:
                vendors_dict[v_id] = {
                    'id': v_id,
                    'name': v_name,
                    'lines': [],
                    'total_current': 0.0,
                    'total_b1': 0.0,
                    'total_b2': 0.0,
                    'total_b3': 0.0,
                    'total_b4': 0.0,
                    'total_older': 0.0,
                    'total_grand': 0.0,
                }

            v_entry = vendors_dict[v_id]
            v_entry['lines'].append({
                'id': ppl.id,
                'name': f"{ppl.name} ({ppl.title})" if ppl.title else ppl.name,
                'invoice_date_display': ppl.request_date.strftime('%m/%d/%Y') if ppl.request_date else '',
                'due_date_display': due_date_val.strftime('%m/%d/%Y') if due_date_val else '',
                'overdue_days': days,
                'current_amount': c_amt,
                'current_amount_fmt': self._format_rupiah(c_amt),
                'b1': b1_amt,
                'b1_fmt': self._format_rupiah(b1_amt),
                'b2': b2_amt,
                'b2_fmt': self._format_rupiah(b2_amt),
                'b3': b3_amt,
                'b3_fmt': self._format_rupiah(b3_amt),
                'b4': b4_amt,
                'b4_fmt': self._format_rupiah(b4_amt),
                'older': older_amt,
                'older_fmt': self._format_rupiah(older_amt),
                'total_amount': amt,
                'total_amount_fmt': self._format_rupiah(amt),
            })

            v_entry['total_current'] += c_amt
            v_entry['total_b1'] += b1_amt
            v_entry['total_b2'] += b2_amt
            v_entry['total_b3'] += b3_amt
            v_entry['total_b4'] += b4_amt
            v_entry['total_older'] += older_amt
            v_entry['total_grand'] += amt

            grand_totals['current'] += c_amt
            grand_totals['b1'] += b1_amt
            grand_totals['b2'] += b2_amt
            grand_totals['b3'] += b3_amt
            grand_totals['b4'] += b4_amt
            grand_totals['older'] += older_amt
            grand_totals['total'] += amt

        res_vendors = []
        for v_id, v_data in vendors_dict.items():
            v_data['total_current_fmt'] = self._format_rupiah(v_data['total_current'])
            v_data['total_b1_fmt'] = self._format_rupiah(v_data['total_b1'])
            v_data['total_b2_fmt'] = self._format_rupiah(v_data['total_b2'])
            v_data['total_b3_fmt'] = self._format_rupiah(v_data['total_b3'])
            v_data['total_b4_fmt'] = self._format_rupiah(v_data['total_b4'])
            v_data['total_older_fmt'] = self._format_rupiah(v_data['total_older'])
            v_data['total_grand_fmt'] = self._format_rupiah(v_data['total_grand'])
            res_vendors.append(v_data)

        h_b1 = f"1-{interval}"
        h_b2 = f"{interval + 1}-{interval * 2}"
        h_b3 = f"{interval * 2 + 1}-{interval * 3}"
        h_b4 = f"{interval * 3 + 1}-{interval * 4}"

        return {
            'as_of_date': as_of_str,
            'as_of_date_display': as_of_dt.strftime('%m/%d/%Y') if as_of_dt else '',
            'based_on': based_on,
            'period_days': period_days,
            'target_move': target_move,
            'partner_id': partner_id,
            'has_unposted': unposted_count > 0,
            'vendors': res_vendors,
            'vendors_list': vendors_list,
            'headers': {
                'at_date': 'At Date',
                'b1': h_b1,
                'b2': h_b2,
                'b3': h_b3,
                'b4': h_b4,
                'older': 'Older',
            },
            'grand_totals': {
                'current_fmt': self._format_rupiah(grand_totals['current']),
                'b1_fmt': self._format_rupiah(grand_totals['b1']),
                'b2_fmt': self._format_rupiah(grand_totals['b2']),
                'b3_fmt': self._format_rupiah(grand_totals['b3']),
                'b4_fmt': self._format_rupiah(grand_totals['b4']),
                'older_fmt': self._format_rupiah(grand_totals['older']),
                'total_fmt': self._format_rupiah(grand_totals['total']),
            },
            'company_name': self.env.company.name,
        }
