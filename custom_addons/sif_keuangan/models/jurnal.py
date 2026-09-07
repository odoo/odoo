# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class SifJurnalEntry(models.Model):
    _name = 'sif.jurnal.entry'
    _description = 'Entri Jurnal Keuangan'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Nomor Bukti',
        required=True,
        copy=False,
        readonly=True,
        default='Draft'
    )
    date = fields.Date(
        string='Tanggal',
        required=True,
        default=fields.Date.context_today
    )

    # Sinkronisasi ganda field agar aman di seluruh tampilan
    ref = fields.Char(string='Referensi / No. Dokumen')
    reference = fields.Char(string='Referensi')

    kwitansi_ref = fields.Char(string='No. Kwitansi')
    project_code = fields.Char(string='Kode Proyek', default='000')
    project_name = fields.Char(string='Nama Proyek', default='KANTOR')
    unit_name = fields.Char(string='Unit Kerja')
    partner_name = fields.Char(string='Pihak Ketiga / Vendor')
    narration = fields.Text(string='Keterangan Transaksi')

    source_type = fields.Selection([
        ('manual', 'Manual'),
        ('ppl', 'PPL (Pengadaan)'),
        ('asset_buy', 'Perolehan Aset'),
        ('asset_depr', 'Penyusutan Aset'),
    ], string='Sumber Transaksi', default='manual')

    line_ids = fields.One2many(
        'sif.jurnal.line', 
        'entry_id', 
        string='Baris Jurnal'
    )

    total_debit = fields.Float(
        string='Total Debet', 
        compute='_compute_totals', 
        store=True
    )
    total_credit = fields.Float(
        string='Total Kredit', 
        compute='_compute_totals', 
        store=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Dibatalkan')
    ], string='Status', default='posted')

    @api.depends('line_ids.debit', 'line_ids.credit')
    def _compute_totals(self):
        for rec in self:
            rec.total_debit = sum(rec.line_ids.mapped('debit'))
            rec.total_credit = sum(rec.line_ids.mapped('credit'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference') and not vals.get('ref'):
                vals['ref'] = vals['reference']
            elif vals.get('ref') and not vals.get('reference'):
                vals['reference'] = vals['ref']

            if vals.get('name', 'Draft') == 'Draft':
                seq = self.env['ir.sequence'].next_by_code('sif.jurnal.number')
                if seq:
                    vals['name'] = seq
                else:
                    prefix = 'J' + fields.Date.today().strftime('%y%m')
                    vals['name'] = f"{prefix}0001"
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('reference') and 'ref' not in vals:
            vals['ref'] = vals['reference']
        elif vals.get('ref') and 'reference' not in vals:
            vals['reference'] = vals['ref']
        return super().write(vals)

    def action_post(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("Rincian baris jurnal tidak boleh kosong!")
            if round(rec.total_debit, 2) != round(rec.total_credit, 2):
                raise UserError(f"Jurnal tidak seimbang! Total Debet (Rp {rec.total_debit:,.2f}) != Total Kredit (Rp {rec.total_credit:,.2f}).")
            rec.state = 'posted'

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    # =========================================================================
    # INTEGRASI MODUL PPL
    # =========================================================================
    @api.model
    def create_journal_from_ppl(self, vals):
        """Penerima pemanggilan action_pay langsung dari modul PPL"""
        if not isinstance(vals, dict):
            return self.create_ppl_journal(vals)

        ppl_id = vals.get('ppl_id') or vals.get('id')
        if ppl_id and 'sifnext.ppl' in self.env:
            ppl_doc = self.env['sifnext.ppl'].browse(ppl_id)
            if ppl_doc.exists():
                return self.create_ppl_journal(ppl_doc)

        lines = []
        raw_lines = vals.get('line_ids') or vals.get('lines') or []
        for line in raw_lines:
            if isinstance(line, (list, tuple)) and len(line) == 3:
                lines.append(line)
            elif isinstance(line, dict):
                lines.append((0, 0, line))

        unit_str = (
            vals.get('unit_name') or 
            vals.get('unit') or 
            vals.get('department_name') or 
            ''
        )
        kwitansi_str = (
            vals.get('kwitansi_ref') or 
            vals.get('kwitansi') or 
            vals.get('receipt_no') or 
            vals.get('payment_ref') or 
            ''
        )
        proj_code = vals.get('project_code') or '000'
        proj_name = vals.get('project_name') or 'KANTOR'

        if not lines:
            debit_acc = vals.get('expense_account_id') or vals.get('debit_account_id') or vals.get('account_id')
            credit_acc = vals.get('payment_account_id') or vals.get('credit_account_id')
            amount = vals.get('amount') or vals.get('total_amount', 0.0)
            desc = vals.get('narration') or vals.get('description') or vals.get('name', 'Realisasi PPL')

            if debit_acc and credit_acc:
                lines = [
                    (0, 0, {
                        'name': desc,
                        'account_id': debit_acc if isinstance(debit_acc, int) else debit_acc.id,
                        'debit': amount,
                        'credit': 0.0,
                        'unit_name': unit_str,
                        'project_code': proj_code,
                    }),
                    (0, 0, {
                        'name': f"Pembayaran {desc}",
                        'account_id': credit_acc if isinstance(credit_acc, int) else credit_acc.id,
                        'debit': 0.0,
                        'credit': amount,
                        'unit_name': unit_str,
                        'project_code': proj_code,
                    })
                ]

        judul_ppl = vals.get('title') or vals.get('subject') or vals.get('name') or ''
        narration_text = vals.get('narration') or vals.get('description') or (f"Realisasi Belanja PPL: {judul_ppl}" if judul_ppl else "Realisasi Belanja PPL")

        entry_vals = {
            'date': vals.get('date') or vals.get('payment_date') or fields.Date.today(),
            'ref': vals.get('ref') or vals.get('reference') or vals.get('name', ''),
            'reference': vals.get('reference') or vals.get('ref') or vals.get('name', ''),
            'kwitansi_ref': kwitansi_str,
            'project_code': proj_code,
            'project_name': proj_name,
            'unit_name': unit_str,
            'partner_name': vals.get('partner_name') or vals.get('vendor_name', ''),
            'narration': narration_text,
            'source_type': 'ppl',
            'state': 'posted',
        }
        if lines:
            entry_vals['line_ids'] = lines

        return self.create(entry_vals)

    @api.model
    def create_ppl_journal(self, ppl_doc):
        """Membuat jurnal otomatis dari objek recordset PPL"""
        payment_acc = getattr(ppl_doc, 'payment_account_id', False)
        if not payment_acc:
            raise UserError(f"Gagal memproses jurnal: Akun Kas/Bank pembayar pada PPL {ppl_doc.name} belum dipilih!")

        details = getattr(ppl_doc, 'detail_ids', [])
        if not details:
            raise UserError(f"Gagal memproses jurnal: Dokumen PPL {ppl_doc.name} tidak memiliki rincian kebutuhan!")

        unit_str = ppl_doc.unit_id.name if hasattr(ppl_doc, 'unit_id') and ppl_doc.unit_id else ''
        partner_str = ppl_doc.vendor_id.name if hasattr(ppl_doc, 'vendor_id') and ppl_doc.vendor_id else ''
        proj_code = getattr(ppl_doc, 'project_code', '000') or '000'
        proj_name = getattr(ppl_doc, 'project_name', 'KANTOR') or 'KANTOR'
        kwitansi_str = getattr(ppl_doc, 'payment_ref', getattr(ppl_doc, 'kwitansi_ref', ''))

        lines = []
        for line in details:
            if not line.account_id:
                raise UserError(f"Akun COA pada item '{line.name}' di PPL {ppl_doc.name} belum diisi!")
            subtotal = getattr(line, 'subtotal', getattr(line, 'total_price', 0.0))
            lines.append((0, 0, {
                'name': f"PPL: {line.name}",
                'account_id': line.account_id.id,
                'debit': subtotal,
                'credit': 0.0,
                'project_code': proj_code,
                'unit_name': unit_str,
            }))

        lines.append((0, 0, {
            'name': f"Pembayaran PPL {ppl_doc.name}",
            'account_id': payment_acc.id,
            'debit': 0.0,
            'credit': ppl_doc.total_amount,
            'project_code': proj_code,
            'unit_name': unit_str,
        }))

        entry = self.create({
            'date': getattr(ppl_doc, 'payment_date', fields.Date.today()),
            'ref': ppl_doc.name,
            'reference': ppl_doc.name,
            'kwitansi_ref': kwitansi_str,
            'project_code': proj_code,
            'project_name': proj_name,
            'unit_name': unit_str,
            'partner_name': partner_str,
            'narration': f"Realisasi Belanja PPL: {ppl_doc.name} - {getattr(ppl_doc, 'title', '')}",
            'source_type': 'ppl',
            'state': 'posted',
            'line_ids': lines,
        })
        return entry

    # =========================================================================
    # INTEGRASI MODUL ASET
    # =========================================================================
    @api.model
    def create_asset_purchase_journal(self, asset_name, asset_code, amount, asset_account_id, credit_account_id, date=False, unit_name='KANTOR', project_code='000', vendor_name='', kwitansi=''):
        """1. Transaksi Perolehan Aset Baru: Debit Aset Tetap, Kredit Hutang Usaha / Kas"""
        keterangan = f"Perolehan Aset: {asset_name} ({asset_code})"
        lines = [
            (0, 0, {
                'name': keterangan,
                'account_id': asset_account_id,
                'debit': amount,
                'credit': 0.0,
                'project_code': project_code,
                'unit_name': unit_name,
            }),
            (0, 0, {
                'name': f"Hutang/Kas Pengadaan: {asset_name}",
                'account_id': credit_account_id,
                'debit': 0.0,
                'credit': amount,
                'project_code': project_code,
                'unit_name': unit_name,
            })
        ]
        return self.create({
            'date': date or fields.Date.today(),
            'ref': asset_code,
            'reference': asset_code,
            'kwitansi_ref': kwitansi,
            'project_code': project_code,
            'unit_name': unit_name,
            'partner_name': vendor_name,
            'narration': keterangan,
            'source_type': 'asset_buy',
            'state': 'posted',
            'line_ids': lines,
        })

    @api.model
    def create_asset_depreciation_journal(self, asset_name, asset_code, amount, dep_account_id, exp_account_id, date, period_name, unit_name='KANTOR', project_code='000'):
        """2. Transaksi Depresiasi Bulanan: Debit Beban Penyusutan, Kredit Akumulasi Penyusutan (24007)"""
        keterangan = f"Akumulasi Penyusutan {asset_name} {period_name}"
        lines = [
            (0, 0, {
                'name': keterangan,
                'account_id': exp_account_id,
                'debit': amount,
                'credit': 0.0,
                'project_code': project_code,
                'unit_name': unit_name,
            }),
            (0, 0, {
                'name': keterangan,
                'account_id': dep_account_id,
                'debit': 0.0,
                'credit': amount,
                'project_code': project_code,
                'unit_name': unit_name,
            })
        ]
        return self.create({
            'date': date,
            'ref': asset_code,
            'reference': asset_code,
            'project_code': project_code,
            'unit_name': unit_name,
            'narration': keterangan,
            'source_type': 'asset_depr',
            'state': 'posted',
            'line_ids': lines,
        })


class SifJurnalLine(models.Model):
    _name = 'sif.jurnal.line'
    _description = 'Baris Jurnal Buku Besar'
    _order = 'date desc, id desc'

    entry_id = fields.Many2one('sif.jurnal.entry', string='Jurnal Bukti', ondelete='cascade')
    date = fields.Date(related='entry_id.date', string='Tanggal', store=True, index=True)
    entry_number = fields.Char(related='entry_id.name', string='Nomor Bukti', store=True, index=True)
    ref = fields.Char(related='entry_id.ref', string='Referensi', store=True)
    reference = fields.Char(related='entry_id.reference', string='Referensi', store=True)
    kwitansi_ref = fields.Char(related='entry_id.kwitansi_ref', string='Kwitansi', store=True)

    project_code = fields.Char(related='entry_id.project_code', string='Kode Proy', store=True, index=True)
    project_name = fields.Char(related='entry_id.project_name', string='Nama Proj', store=True)
    unit_name = fields.Char(related='entry_id.unit_name', string='Unit Kerja', store=True, index=True)
    partner_name = fields.Char(related='entry_id.partner_name', string='Pihak Ketiga', store=True)

    account_id = fields.Many2one('sif.coa', string='Account', required=True, index=True)
    account_code = fields.Char(related='account_id.code', string='Kode Akun', store=True)
    account_name = fields.Char(related='account_id.name', string='Nama Akun', store=True)

    name = fields.Char(string='Keterangan', required=True)
    debit = fields.Float(string='Debet', default=0.0)
    credit = fields.Float(string='Kredit', default=0.0)


class SifBukuBesarWizard(models.TransientModel):
    _name = 'sif.buku.besar.wizard'
    _description = 'Filter Periode Buku Besar'

    date_from = fields.Date(
        string='Tanggal Awal', 
        required=True, 
        default=lambda self: fields.Date.context_today(self).replace(day=1)
    )
    date_to = fields.Date(
        string='Tanggal Akhir', 
        required=True, 
        default=fields.Date.context_today
    )
    account_id = fields.Many2one('sif.coa', string='Account (Opsional)')
    project_code = fields.Char(string='Kode Proyek (Opsional)')
    unit_name = fields.Char(string='Unit Kerja (Opsional)')

    def action_open_buku_besar(self):
        self.ensure_one()
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        if self.account_id:
            domain.append(('account_id', '=', self.account_id.id))
        if self.project_code:
            domain.append(('project_code', '=', self.project_code))
        if self.unit_name:
            domain.append(('unit_name', 'ilike', self.unit_name))

        tgl_awal = self.date_from.strftime('%d/%m/%Y')
        tgl_akhir = self.date_to.strftime('%d/%m/%Y')

        return {
            'name': f"Buku Besar ({tgl_awal} s/d {tgl_akhir})",
            'type': 'ir.actions.act_window',
            'res_model': 'sif.jurnal.line',
            'view_mode': 'list',
            'views': [(self.env.ref('sif_keuangan.view_sif_buku_besar_list').id, 'list')],
            'domain': domain,
            'context': {},
            'target': 'current',
        }