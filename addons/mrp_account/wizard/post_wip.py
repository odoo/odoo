# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo import fields, models, _, api, Command
from odoo.exceptions import UserError


class PostWipLine(models.TransientModel):
    _name = 'mrp.account.post.wip.line'
    _description = 'Line to be created for posting WIP'

    account_id = fields.Many2one('account.account', "Account")
    label = fields.Char("Label")
    debit = fields.Monetary("Debit", compute='_compute_debit', store=True, readonly=False)
    credit = fields.Monetary("Credit", compute='_compute_credit', store=True, readonly=False)
    currency_id = fields.Many2one('res.currency', "Currency", default=lambda self: self.env.company.currency_id)
    post_wip_id = fields.Many2one('mrp.account.post.wip', "Post WIP wizard")

    _sql_constraints = [
        ('check_debit_credit', 'CHECK ( debit = 0 OR credit = 0 )',
         'A single line cannot be both credit and debit.')
    ]

    @api.depends('credit')
    def _compute_debit(self):
        for record in self:
            if not record.currency_id.is_zero(record.credit):
                record.debit = 0

    @api.depends('debit')
    def _compute_credit(self):
        for record in self:
            if not record.currency_id.is_zero(record.debit):
                record.credit = 0


class PostWip(models.TransientModel):
    _name = 'mrp.account.post.wip'
    _description = 'Post Manufacturing WIP'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'date' in fields_list:
            date = self.env.context.get('date')
            res['date'] = fields.Datetime.from_string(date) if date else fields.Datetime.now()
            res['reversal_date'] = res['date'] + timedelta(days=1)
        if 'journal_id' in fields_list:
            default = self.env['ir.property']._get_default_property('property_stock_journal', 'product.category')[1]
            if default:
                res['journal_id'] = default[1]
        if 'reference' in fields_list:
            res['reference'] = _('Manufacturing - WIP')
        if 'line_ids' in fields_list:
            res['line_ids'] = self._generate_lines()
        return res

    date = fields.Date("Date")
    reversal_date = fields.Date("Reversal Date")
    journal_id = fields.Many2one('account.journal', "Journal")
    reference = fields.Char("Reference")
    line_ids = fields.One2many('mrp.account.post.wip.line', 'post_wip_id', "Post WIP lines")

    def _get_overhead_account(self):
        overhead_account = self.env.company.account_production_wip_overhead_account_id
        if overhead_account:
            return overhead_account.id
        cop_acc = self.env['ir.property']._get_default_property('property_stock_account_production_cost_id', 'product.category')[1]
        if cop_acc:
            return cop_acc[1]
        return self.env['ir.property']._get_default_property('property_stock_account_input_categ_id', 'product.category')[1]

    def _generate_lines(self):
        productions = self.env['mrp.production'].search([('state', 'in', ('progress', 'to_close', 'confirmed'))])
        compo_value = -sum(
            move.product_id._prepare_out_svl_vals(move.quantity, None)['value']
            for move in productions.move_raw_ids.filtered(lambda m: m.picked and m.quantity)
        )
        overhead_value = productions.workorder_ids._cal_cost()
        sval_acc = self.env['ir.property']._get_default_property('property_stock_valuation_account_id', 'product.category')[1]
        sval_acc = sval_acc[1] if sval_acc else False
        return [
            Command.create({
                'label': _('WIP - Component Value'),
                'credit': compo_value,
                'account_id': sval_acc,
            }),
            Command.create({
                'label': _('WIP - Overhead'),
                'credit': overhead_value,
                'account_id': self._get_overhead_account(),
            }),
            Command.create({
                'label': _('Manufacturing - WIP'),
                'debit': compo_value + overhead_value,
                'account_id': self.env.company.account_production_wip_account_id.id,
            })
        ]

    def confirm(self):
        if self.env.company.currency_id.compare_amounts(sum(self.line_ids.mapped('credit')), sum(self.line_ids.mapped('debit'))):
            raise UserError(_('Please make sure the total credit amount equals the total debit amount.'))
        move = self.env['account.move'].sudo().create({
            'journal_id': self.journal_id.id,
            'date': self.date,
            'ref': self.reference,
            'move_type': 'entry',
            'line_ids': [
                Command.create({
                    'name': line.label,
                    'account_id': line.account_id.id,
                    'debit': line.debit,
                    'credit': line.credit,
                }) for line in self.line_ids
            ]
        })
        move._post()
        move._reverse_moves(default_values_list=[{
            'ref': _('Reversal of: %s', self.reference),
            'date': self.reversal_date,
        }])._post()
