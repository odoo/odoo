# -*- coding: utf-8 -*-
from odoo import fields, models


class MultipleInvoice(models.Model):
    """Multiple Invoice Model"""
    _name = "multiple.invoice"
    _description = 'Multiple Invoice'
    _order = "sequence"

    sequence = fields.Integer('Sequence No')
    copy_name = fields.Char('Invoice Copy Name')
    journal_id = fields.Many2one('account.journal', string="Journal")


class AccountJournal(models.Model):
    """Inheriting Account Journal Model"""
    _inherit = "account.journal"

    multiple_invoice_ids = fields.One2many('multiple.invoice', 'journal_id',
                                           string='Multiple Invoice')
    multiple_invoice_type = fields.Selection(
        [('text', 'Text'), ('watermark', 'Watermark')], required=True,
        default='text', string="Display Type")

    text_position = fields.Selection([
        ('header', 'Header'),
        ('footer', 'Footer'),
        ('body', 'Document Body')
    ], required=True, default='header')

    body_text_position = fields.Selection([
        ('tl', 'Top Left'),
        ('tr', 'Top Right'),
        ('bl', 'Bottom Left'),
        ('br', 'Bottom Right'),

    ], default='tl')

    text_align = fields.Selection([
        ('right', 'Right'),
        ('left', 'Left'),
        ('center', 'Center'),

    ], default='right')

    layout = fields.Char(related="company_id.external_report_layout_id.key")