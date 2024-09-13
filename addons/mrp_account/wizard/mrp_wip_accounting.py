# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo import fields, models, _, api, Command
from odoo.exceptions import UserError
from odoo.tools import format_list


class MrpWipAccountingLine(models.TransientModel):
    _name = 'mrp.account.wip.accounting.line'
    _description = 'Account move line to be created when posting WIP account move'

    account_id = fields.Many2one('account.account', "Account")
    label = fields.Char("Label")
    debit = fields.Monetary("Debit", compute='_compute_debit', store=True, readonly=False)
    credit = fields.Monetary("Credit", compute='_compute_credit', store=True, readonly=False)
    currency_id = fields.Many2one('res.currency', "Currency", default=lambda self: self.env.company.currency_id)
    wip_accounting_id = fields.Many2one('mrp.account.wip.accounting', "WIP accounting wizard")

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


class MrpWipAccounting(models.TransientModel):
    _name = 'mrp.account.wip.accounting'
    _description = 'Wizard to post Manufacturing WIP account move'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        productions = self.env['mrp.production'].browse(self.env.context.get('active_ids'))
        # ignore selected MOs that aren't a WIP
        productions = productions.filtered(lambda mo: mo.state in ['progress', 'to_close', 'confirmed'])
        if 'journal_id' in fields_list:
            default = self.env['ir.property']._get_default_property('property_stock_journal', 'product.category')[1]
            if default:
                res['journal_id'] = default[1]
        if 'reference' in fields_list:
            res['reference'] = _('Manufacturing WIP - %(orders_list)s', orders_list=productions and format_list(self.env, productions.mapped('name')) or _("Manual Entry"))
        if 'line_ids' in fields_list:
            res['line_ids'] = self._get_line_vals(productions)
        if 'mo_ids' in fields_list:
            res['mo_ids'] = [Command.set(productions.ids)]
        return res

    date = fields.Date("Date", default=fields.Datetime.now)
    reversal_date = fields.Date(
        "Reversal Date", compute="_compute_reversal_date", required=True,
        readonly=False, store=True, precompute=True)
    journal_id = fields.Many2one('account.journal', "Journal", required=True)
    reference = fields.Char("Reference")
    line_ids = fields.One2many('mrp.account.wip.accounting.line', 'wip_accounting_id', "WIP accounting lines")
    mo_ids = fields.Many2many('mrp.production')

    def _get_overhead_account(self):
        overhead_account = self.env.company.account_production_wip_overhead_account_id
        if overhead_account:
            return overhead_account.id
        cop_acc = self.env['ir.property']._get_default_property('property_stock_account_production_cost_id', 'product.category')[1]
        if cop_acc:
            return cop_acc[1]
        return self.env['ir.property']._get_default_property('property_stock_account_input_categ_id', 'product.category')[1]

    def _get_line_vals(self, productions=False):
        if not productions:
            productions = self.env['mrp.production']
        compo_value = sum(
            ml.quantity_product_uom * (ml.product_id.lot_valuated and ml.lot_id and ml.lot_id.standard_price or ml.product_id.standard_price)
            for ml in productions.move_raw_ids.move_line_ids.filtered(lambda ml: ml.picked and ml.quantity)
        )
        overhead_value = productions.workorder_ids._cal_cost()
        sval_acc = self.env['ir.property']._get_default_property('property_stock_valuation_account_id', 'product.category')[1]
        sval_acc = sval_acc[1] if sval_acc else False
        return [
            Command.create({
                'label': _("WIP - Component Value"),
                'credit': compo_value,
                'account_id': sval_acc,
            }),
            Command.create({
                'label': _("WIP - Overhead"),
                'credit': overhead_value,
                'account_id': self._get_overhead_account(),
            }),
            Command.create({
                'label': _("Manufacturing WIP - %(orders_list)s", orders_list=productions and format_list(self.env, productions.mapped('name')) or _("Manual Entry")),
                'debit': compo_value + overhead_value,
                'account_id': self.env.company.account_production_wip_account_id.id,
            })
        ]

    @api.depends('date')
    def _compute_reversal_date(self):
        for wizard in self:
            if not wizard.reversal_date or wizard.reversal_date <= wizard.date:
                wizard.reversal_date = wizard.date + relativedelta(days=1)
            else:
                wizard.reversal_date = wizard.reversal_date

    def confirm(self):
        self.ensure_one()
        if self.env.company.currency_id.compare_amounts(sum(self.line_ids.mapped('credit')), sum(self.line_ids.mapped('debit'))) != 0:
            raise UserError(_("Please make sure the total credit amount equals the total debit amount."))
        if self.reversal_date <= self.date:
            raise UserError(_("Reversal date must be after the posting date."))
        move = self.env['account.move'].sudo().create({
            'journal_id': self.journal_id.id,
            'wip_production_ids': self.mo_ids.ids,
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
            'ref': _("Reversal of: %s", self.reference),
            'wip_production_ids': self.mo_ids.ids,
            'date': self.reversal_date,
        }])._post()
