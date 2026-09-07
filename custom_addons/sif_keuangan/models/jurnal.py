# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class SifJurnalEntry(models.Model):
    _name = 'sif.jurnal.entry'
    _description = 'Dokumen Jurnal Transaksi Keuangan'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Nomor Bukti',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    date = fields.Date(
        string='Tanggal',
        required=True,
        default=fields.Date.context_today
    )
    ref = fields.Char(
        string='Referensi / Dokumen Sumber'
    )
    kwitansi_ref = fields.Char(
        string='No. Kwitansi / Bukti Fisik'
    )
    unit_name = fields.Char(
        string='Unit Kerja',
        default='KANTOR'
    )
    source_type = fields.Selection([
        ('manual', 'Input Manual'),
        ('ppl', 'PPL / Pengadaan'),
        ('asset_buy', 'Perolehan Aset'),
        ('asset_depr', 'Depresiasi Aset'),
    ], string='Sumber Transaksi', default='manual', required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('cancel', 'Dibatalkan'),
    ], string='Status', default='draft', required=True, tracking=True)

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

    # Helper Periode Bulanan
    period_month = fields.Integer(
        string='Bulan Periode',
        compute='_compute_period',
        store=True
    )
    period_year = fields.Integer(
        string='Tahun Periode',
        compute='_compute_period',
        store=True
    )
    period_key = fields.Char(
        string='Kunci Periode',
        compute='_compute_period',
        store=True
    )

    @api.depends('date')
    def _compute_period(self):
        for rec in self:
            if rec.date:
                rec.period_month = rec.date.month
                rec.period_year = rec.date.year
                rec.period_key = rec.date.strftime('%Y-%m')
            else:
                rec.period_month = 0
                rec.period_year = 0
                rec.period_key = ''

    @api.depends('line_ids.debit', 'line_ids.credit')
    def _compute_totals(self):
        for rec in self:
            rec.total_debit = sum(rec.line_ids.mapped('debit'))
            rec.total_credit = sum(rec.line_ids.mapped('credit'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('sif.jurnal.entry')
                if seq:
                    vals['name'] = seq
                else:
                    date_val = fields.Date.to_date(vals.get('date')) or fields.Date.today()
                    prefix = f"J{date_val.strftime('%y%m')}"
                    last_rec = self.search([('name', '=like', f"{prefix}%")], order='id desc', limit=1)
                    next_num = 1
                    if last_rec and len(last_rec.name) >= 10:
                        try:
                            next_num = int(last_rec.name[-4:]) + 1
                        except ValueError:
                            next_num = 1
                    vals['name'] = f"{prefix}{next_num:04d}"
        return super(SifJurnalEntry, self).create(vals_list)

    def action_post(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_('Transaksi jurnal tidak memiliki baris rincian debet/kredit.'))
            if len(rec.line_ids) < 2:
                raise UserError(_('Jurnal harus memiliki minimal 2 baris (Debet dan Kredit).'))
            if round(rec.total_debit, 2) != round(rec.total_credit, 2):
                raise ValidationError(_(
                    'Jurnal tidak balance!\nTotal Debet: {:,.2f}\nTotal Kredit: {:,.2f}'
                ).format(rec.total_debit, rec.total_credit))
            rec.state = 'posted'

    def action_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    # -------------------------------------------------------------------------
    # INTEGRASI RPC MODUL PPL
    # -------------------------------------------------------------------------
    @api.model
    def create_journal_from_ppl(self, vals):
        """
        RPC Method untuk pencatatan otomatis transaksi PPL saat dibayar / dicairkan.
        Menerima payload dictionary maupun objek recordset PPL.
        """
        # Penanganan jika parameter berupa objek recordset PPL
        if hasattr(vals, '_name'):
            ppl = vals
            vals = {
                'date': ppl.payment_date if hasattr(ppl, 'payment_date') and ppl.payment_date else fields.Date.today(),
                'ref': ppl.name if hasattr(ppl, 'name') else 'PPL',
                'kwitansi_ref': getattr(ppl, 'kwitansi_ref', '') or getattr(ppl, 'receipt_number', ''),
                'unit_name': getattr(ppl, 'unit_name', '') or (ppl.department_id.name if hasattr(ppl, 'department_id') and ppl.department_id else 'KANTOR'),
                'source_type': 'ppl',
                'lines': []
            }
            # Ambil data nominal dan akun jika tersedia di model PPL
            dpp = getattr(ppl, 'amount_untaxed', 0.0) or getattr(ppl, 'amount_dpp', 0.0)
            ppn = getattr(ppl, 'amount_tax', 0.0) or getattr(ppl, 'amount_ppn', 0.0)
            total = getattr(ppl, 'amount_total', 0.0) or (dpp + ppn)

            exp_acc = getattr(ppl, 'expense_account_id', False)
            ppn_acc = getattr(ppl, 'tax_account_id', False) or getattr(ppl, 'ppn_account_id', False)
            pay_acc = getattr(ppl, 'payment_account_id', False) or getattr(ppl, 'bank_account_id', False)

            if exp_acc and pay_acc:
                lines = []
                if dpp > 0:
                    lines.append({
                        'account_id': exp_acc.id,
                        'name': f"Biaya Pengadaan {vals['ref']}",
                        'debit': dpp,
                        'credit': 0.0
                    })
                if ppn > 0 and ppn_acc:
                    lines.append({
                        'account_id': ppn_acc.id,
                        'name': f"PPN Masukan (Aset) {vals['ref']}",
                        'debit': ppn,
                        'credit': 0.0
                    })
                lines.append({
                    'account_id': pay_acc.id,
                    'name': f"Pembayaran {vals['ref']}",
                    'debit': 0.0,
                    'credit': total
                })
                vals['lines'] = lines

        # Pemrosesan jika parameter dictionary
        lines_command = []
        raw_lines = vals.get('lines', [])
        for l in raw_lines:
            lines_command.append((0, 0, {
                'account_id': l.get('account_id'),
                'name': l.get('name', 'Transaksi PPL'),
                'debit': l.get('debit', 0.0),
                'credit': l.get('credit', 0.0),
            }))

        entry_vals = {
            'date': vals.get('date', fields.Date.today()),
            'ref': vals.get('ref', 'PPL'),
            'kwitansi_ref': vals.get('kwitansi_ref', ''),
            'unit_name': vals.get('unit_name', 'KANTOR'),
            'source_type': 'ppl',
            'line_ids': lines_command,
        }

        entry = self.sudo().create(entry_vals)
        if entry.line_ids:
            entry.action_post()
        return entry

    # -------------------------------------------------------------------------
    # INTEGRASI RPC MODUL ASET
    # -------------------------------------------------------------------------
    @api.model
    def create_asset_purchase_journal(self, asset_name, asset_code, amount,
                                     asset_account_id, credit_account_id,
                                     date=False, unit_name='KANTOR',
                                     vendor_name='', kwitansi=''):
        """
        Pencatatan Jurnal Perolehan / Pembelian Aset Tetap.
        Debet : Akun Aset Tetap
        Kredit: Akun Kas / Bank / Hutang Pembelian
        """
        txn_date = date or fields.Date.today()
        ref_label = f"Perolehan Aset: [{asset_code}] {asset_name}"
        if vendor_name:
            ref_label += f" - Vendor: {vendor_name}"

        lines = [
            (0, 0, {
                'account_id': asset_account_id,
                'name': f"Perolehan [{asset_code}] {asset_name}",
                'debit': amount,
                'credit': 0.0,
            }),
            (0, 0, {
                'account_id': credit_account_id,
                'name': f"Pembayaran / Kewajiban Perolehan [{asset_code}]",
                'debit': 0.0,
                'credit': amount,
            })
        ]

        entry = self.sudo().create({
            'date': txn_date,
            'ref': f"AST-BUY/{asset_code}",
            'kwitansi_ref': kwitansi,
            'unit_name': unit_name,
            'source_type': 'asset_buy',
            'line_ids': lines,
        })
        entry.action_post()
        return entry

    @api.model
    def create_asset_depreciation_journal(self, asset_name, asset_code, amount,
                                         dep_account_id, exp_account_id,
                                         date, period_name, unit_name='KANTOR'):
        """
        Pencatatan Jurnal Depresiasi / Penyusutan Berkala Aset.
        Debet : Akun Beban Penyusutan
        Kredit: Akun Akumulasi Penyusutan (Akun Kontra Aset)
        """
        desc = f"Penyusutan [{asset_code}] {asset_name} - Periode {period_name}"
        lines = [
            (0, 0, {
                'account_id': exp_account_id,
                'name': desc,
                'debit': amount,
                'credit': 0.0,
            }),
            (0, 0, {
                'account_id': dep_account_id,
                'name': desc,
                'debit': 0.0,
                'credit': amount,
            })
        ]

        entry = self.sudo().create({
            'date': date or fields.Date.today(),
            'ref': f"DEP/{asset_code}/{period_name}",
            'kwitansi_ref': '',
            'unit_name': unit_name,
            'source_type': 'asset_depr',
            'line_ids': lines,
        })
        entry.action_post()
        return entry


class SifJurnalLine(models.Model):
    _name = 'sif.jurnal.line'
    _description = 'Baris Jurnal Transaksi / Buku Besar'
    _order = 'date desc, id desc'

    entry_id = fields.Many2one(
        'sif.jurnal.entry',
        string='Voucher Jurnal',
        ondelete='cascade',
        required=True
    )
    entry_number = fields.Char(
        related='entry_id.name',
        string='Bukti / Nomer',
        store=True
    )
    date = fields.Date(
        related='entry_id.date',
        string='Tanggal',
        store=True,
        index=True
    )
    unit_name = fields.Char(
        related='entry_id.unit_name',
        string='Unit Kerja',
        store=True
    )
    kwitansi_ref = fields.Char(
        related='entry_id.kwitansi_ref',
        string='Kwitansi',
        store=True
    )
    state = fields.Selection(
        related='entry_id.state',
        string='Status',
        store=True
    )

    account_id = fields.Many2one(
        'sif.coa',
        string='Account',
        required=True,
        index=True
    )
    account_code = fields.Char(
        related='account_id.code',
        string='Kode Akun',
        store=True
    )
    account_name = fields.Char(
        related='account_id.name',
        string='Nama Account',
        store=True
    )

    name = fields.Char(
        string='Keterangan',
        required=True
    )
    debit = fields.Float(
        string='Debet',
        default=0.0
    )
    credit = fields.Float(
        string='Kredit',
        default=0.0
    )
    balance = fields.Float(
        string='Saldo Mutasi',
        compute='_compute_balance',
        store=True
    )
    period_key = fields.Char(
        related='entry_id.period_key',
        string='Periode',
        store=True
    )

    @api.depends('debit', 'credit')
    def _compute_balance(self):
        for rec in self:
            rec.balance = (rec.debit or 0.0) - (rec.credit or 0.0)


class SifBukuBesarWizard(models.TransientModel):
    _name = 'sif.buku.besar.wizard'
    _description = 'Wizard Filter Periode Buku Besar'

    date_from = fields.Date(
        string='Tanggal Awal',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='Tanggal Akhir',
        required=True,
        default=fields.Date.context_today
    )
    account_id = fields.Many2one(
        'sif.coa',
        string='Akun (Opsional)'
    )
    unit_name = fields.Char(
        string='Unit Kerja (Opsional)'
    )

    def action_tampilkan_buku_besar(self):
        self.ensure_one()
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('state', '=', 'posted'),
        ]

        if self.account_id:
            domain.append(('account_id', '=', self.account_id.id))
        if self.unit_name:
            domain.append(('unit_name', 'ilike', self.unit_name))

        return {
            'name': _('Buku Besar: {} s/d {}').format(
                self.date_from.strftime('%d/%m/%Y'),
                self.date_to.strftime('%d/%m/%Y')
            ),
            'type': 'ir.actions.act_window',
            'res_model': 'sif.jurnal.line',
            'view_mode': 'list,form',
            'view_id': self.env.ref('sif_keuangan.sif_jurnal_line_tree_view').id,
            'domain': domain,
            'target': 'current',
        }