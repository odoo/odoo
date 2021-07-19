# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools import float_compare, date_utils, email_split, email_re
from odoo.tools.misc import formatLang, format_date, get_lang

from itertools import groupby
from itertools import zip_longest

class Witholding(models.Model):
    _name = "l10n_ec.witholding"

    company_id = fields.Many2one('res.company')
    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', _('Document Type'))
    witholding_move_id = fields.Many2one('account.move', _('Account Move'))
    invoice_id = fields.Many2one('account.move', _('Origin Document'))
    partner_id = fields.Many2one('res.partner')
    witholding_line_ids = fields.One2many('l10n_ec.witholding.lines', 'witholding_id')
    currency_id = fields.Many2one('res.currency')
    amount_total= fields.Monetary('Total Amount', compute="_compute_amount")
    journal_id = fields.Many2one('account.journal', 'Journal')

    @api.onchange('invoice_id')
    def _on_invoice_change(self):
        lines=[]
        for line in self.invoice_id.invoice_line_ids:
            for tax in line.witholding_tax_ids:
                lines.append((0,0,{
                    'name': tax.name,
                }))

        self.witholding_line_ids=[
            (5,0,0)
        ]+lines
        self.partner_id = self.invoice_id.partner_id
        self.journal_id = self.invoice_id.journal_id

    @api.depends('invoice_id')
    def _compute_amount(self):
        wth_values = self.invoice_id.amount_by_group_wth
        if wth_values:
            self.amount_total = sum([w[1] for w in wth_values])
        else:
            self.amount_total = 0.0

    def valid_wth(self):
        for ret in self:
            inv = ret.invoice_id
            move_data = {
                'journal_id': inv.journal_id.id,
                'ref': 'Retention ' + inv.name,
                'date': inv.invoice_date,
                'l10n_latam_document_type_id': self.env.ref('l10n_ec_extra.ec_03').id
            }
            total_counter = 0
            lines = []
            
            for line in ret._calculate_taxes():
                lines.append((0, 0, {
                    'partner_id': ret.partner_id.id,
                    'account_id': line['account'],
                    'name': 'Retention ' + inv.name,
                    'debit': abs(line['amount']),
                    'credit': 0.00
                }))

                total_counter += abs(line['amount'])
            rec_account = inv.partner_id.property_account_receivable_id.id
            pay_account = inv.partner_id.property_account_payable_id.id
            lines.append((0, 0, {
                'partner_id': ret.partner_id.id,
                'account_id': inv.move_type == 'in_invoice' and pay_account or rec_account,
                'name': 'Ŕetencion' + inv.name,
                'debit': 0.00,
                'credit': total_counter
            }))
            move_data.update({'line_ids': lines})
            move = self.env['account.move'].create(move_data)
            acctype = inv.move_type == 'in_invoice' and 'payable' or 'receivable'
            inv_lines = inv.line_ids
            acc2rec = inv_lines.filtered(lambda l: l.account_id.internal_type == acctype)  # noqa
            acc2rec += move.line_ids.filtered(lambda l: l.account_id.internal_type == acctype)  # noqa
            #acc2rec.auto_reconcile_lines()
            ret.write({'witholding_move_id': move.id})
            move.post()
        return True

    def _calculate_taxes(self):
        ret_taxes = []
        for line in self.invoice_id.invoice_line_ids:
            for tax in line.witholding_tax_ids:
                tax_detail = tax.compute_all(line.price_unit, line.currency_id, line.quantity, line.product_id, self.partner_id)['taxes']
                tax_obj = self.env['account.tax.repartition.line'].search([('id', '=', tax_detail[0]['tax_repartition_line_id'])])[0]
                ret_taxes.append({
                    'group_id': tax.tax_group_id.id,
                    'tax_repartition_line_id': tax_detail[0]['tax_repartition_line_id'],
                    'account': tax_obj.account_id.id,
                    'amount': sum( [t['amount'] for t in tax_detail ]),
                    'base': sum( [t['base'] for t in tax_detail ]),
                    'tax_id': tax.id
                })

        ret_taxes = sorted(ret_taxes, key = lambda x: x['tax_id'])
        ret_to_merge = groupby(ret_taxes, lambda x: x['tax_id'])
        ret_taxes = []
        for k,vv in ret_to_merge:
            v=list(vv)
            ret_taxes.append({
                        'group_id': v[0]['group_id'],
                        'tax_repartition_line_id': v[0]['tax_repartition_line_id'],
                        'amount': sum( [t['amount'] for t in v ]),
                        'base': sum( [t['base'] for t in v ]),
                        'tax_id': v[0]['tax_id'],
                        'account': v[0]['account']
                    })
        return ret_taxes
            
            

class WitholdingLine(models.Model):
    _name = 'l10n_ec.witholding.lines'

    name = fields.Char(_('Tax'))
    witholding_id = fields.Many2one('l10n_ec.witholding')
    currency_id = fields.Many2one('res.currency')
    base = fields.Monetary('Base')
    percent = fields.Float(_('Percent'))
    amount = fields.Monetary(_('Amount'))

