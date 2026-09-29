# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SifLockDate(models.Model):
    _name = 'sif.lock.date'
    _description = 'Kunci Tanggal Akuntansi'

    name = fields.Char(string='Nama', default='Kunci Tanggal', readonly=True)
    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        default=lambda self: self.env.company,
        required=True,
    )
    lock_pendapatan = fields.Date(string='Kunci Tanggal Pendapatan')
    lock_ppl = fields.Date(string='Kunci Tanggal PPL')

    _sql_constraints = [
        ('company_uniq', 'unique(company_id)', 'Hanya boleh satu record kunci per perusahaan.'),
    ]

    @api.model
    def get_or_create(self, company_id=None):
        company_id = company_id or self.env.company.id
        rec = self.search([('company_id', '=', company_id)], limit=1)
        if not rec:
            rec = self.create({'company_id': company_id})
        return rec

    def action_lock_all(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Kunci Semua (PPL & Pendapatan)'),
            'res_model': 'sif.lock.date.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_mode': 'all'},
        }

    def action_lock_pendapatan(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Kunci Tanggal Pendapatan'),
            'res_model': 'sif.lock.date.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_mode': 'pendapatan'},
        }

    def action_lock_ppl(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Kunci Tanggal PPL'),
            'res_model': 'sif.lock.date.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_mode': 'ppl'},
        }


class SifLockDateWizard(models.TransientModel):
    _name = 'sif.lock.date.wizard'
    _description = 'Wizard Kunci Tanggal'

    mode = fields.Selection([
        ('all', 'Kunci Semua (PPL & Pendapatan)'),
        ('pendapatan', 'Kunci Pendapatan'),
        ('ppl', 'Kunci PPL'),
    ], string='Mode', default='all', required=True)

    lock_date = fields.Date(string='Kunci s/d Tanggal', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    def action_save(self):
        lock = self.env['sif.lock.date'].get_or_create(self.company_id.id)
        vals = {}
        if self.mode in ('all', 'pendapatan'):
            vals['lock_pendapatan'] = self.lock_date
        if self.mode in ('all', 'ppl'):
            vals['lock_ppl'] = self.lock_date
        lock.write(vals)

        label = {
            'all': 'PPL & Pendapatan',
            'pendapatan': 'Pendapatan',
            'ppl': 'PPL',
        }.get(self.mode, self.mode)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Kunci Tanggal Berhasil'),
                'message': _(f'Transaksi {label} dikunci s/d {self.lock_date.strftime("%d/%m/%Y")}.'),
                'type': 'success',
                'sticky': False,
            },
        }

    @api.model
    def get_current_locks(self, company_id=None):
        lock = self.env['sif.lock.date'].get_or_create(company_id or self.env.company.id)
        return {
            'lock_pendapatan': fields.Date.to_string(lock.lock_pendapatan) if lock.lock_pendapatan else False,
            'lock_ppl': fields.Date.to_string(lock.lock_ppl) if lock.lock_ppl else False,
        }

    @api.model
    def check_ppl_lock(self, transaction_date):
        lock = self.env['sif.lock.date'].get_or_create()
        if lock.lock_ppl and transaction_date and fields.Date.to_date(transaction_date) <= lock.lock_ppl:
            raise UserError(_(
                'Periode PPL s/d %s sudah dikunci.\n'
                'Transaksi pada tanggal ini tidak diizinkan.'
            ) % lock.lock_ppl.strftime('%d/%m/%Y'))

    @api.model
    def check_pendapatan_lock(self, transaction_date):
        lock = self.env['sif.lock.date'].get_or_create()
        if lock.lock_pendapatan and transaction_date and fields.Date.to_date(transaction_date) <= lock.lock_pendapatan:
            raise UserError(_(
                'Periode Pendapatan s/d %s sudah dikunci.\n'
                'Transaksi pada tanggal ini tidak diizinkan.'
            ) % lock.lock_pendapatan.strftime('%d/%m/%Y'))
