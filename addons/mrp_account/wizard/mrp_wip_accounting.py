# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, time
from dateutil.relativedelta import relativedelta

from odoo import fields, models, _, api, Command
from odoo.exceptions import UserError


class MrpAccountWipAccountingLine(models.TransientModel):
    _name = 'mrp.account.wip.accounting.line'
    _description = 'Account move line to be created when posting WIP account move'

    account_id = fields.Many2one('account.account', "Account")
    label = fields.Char("Label")
    debit = fields.Monetary("Debit", compute='_compute_debit', store=True, readonly=False)
    credit = fields.Monetary("Credit", compute='_compute_credit', store=True, readonly=False)
    currency_id = fields.Many2one('res.currency', "Currency", default=lambda self: self.env.company.currency_id)
    wip_accounting_id = fields.Many2one('mrp.account.wip.accounting', "WIP accounting wizard")

    _check_debit_credit = models.Constraint(
        'CHECK ( debit = 0 OR credit = 0 )',
        'A single line cannot be both credit and debit.',
    )

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


class MrpAccountWipAccounting(models.TransientModel):
    _name = 'mrp.account.wip.accounting'
    _description = 'Wizard to post Manufacturing WIP account move'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        productions = self.env['mrp.production'].browse(self.env.context.get('active_ids'))
        # ignore selected MOs that aren't a WIP
        productions = productions.filtered(lambda mo: mo.state in ['progress', 'to_close', 'confirmed'])
        if 'journal_id' in fields:
            default = self.env['product.category']._fields['property_stock_journal'].get_company_dependent_fallback(self.env['product.category'])
            if default:
                res['journal_id'] = default.id
        if 'reference' in fields:
            res['reference'] = _("Manufacturing WIP - %(orders_list)s", orders_list=productions.mapped('name') or _("Manual Entry"))
        if 'mo_ids' in fields:
            res['mo_ids'] = [Command.set(productions.ids)]
        return res

    date = fields.Date("Date", default=fields.Datetime.now)
    reversal_date = fields.Date(
        "Reversal Date", compute="_compute_reversal_date", required=True,
        store=True, readonly=False)
    journal_id = fields.Many2one('account.journal', "Journal", required=True)
    reference = fields.Char("Reference")
    line_ids = fields.One2many(
        'mrp.account.wip.accounting.line', 'wip_accounting_id', "WIP accounting lines",
        compute="_compute_line_ids", store=True, readonly=False)
    mo_ids = fields.Many2many('mrp.production')

    def _get_overhead_account(self):
        overhead_account = self.env.company.account_production_wip_overhead_account_id
        if overhead_account:
            return overhead_account.id
        ProductCategory = self.env['product.category']
        return ProductCategory._fields['property_stock_account_production_cost_id'].get_company_dependent_fallback(ProductCategory).id

    def _get_line_vals(self, productions=False, date=False):
        if not productions:
            productions = self.env['mrp.production']
        if not date:
            date = datetime.now().replace(hour=23, minute=59, second=59)
        compo_value = sum(
            ml.quantity_product_uom * (ml.product_id.lot_valuated and ml.lot_id and ml.lot_id.standard_price or ml.product_id.standard_price)
            for ml in productions.move_raw_ids.move_line_ids.filtered(lambda ml: ml.picked and ml.quantity and ml.date <= date)
        )
        overhead_value = productions.workorder_ids._cal_cost(date)
        sval_acc = self.env['product.category']._fields['property_stock_valuation_account_id'].get_company_dependent_fallback(self.env['product.category']).id
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
                'label': _("Manufacturing WIP - %(orders_list)s", orders_list=productions.mapped('name') or _("Manual Entry")),
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

    @api.depends('date')
    def _compute_line_ids(self):
        for wizard in self:
            # don't update lines when manual (i.e. no applicable MOs) entry
            if not wizard.line_ids or wizard.mo_ids:
                wizard.line_ids = [Command.clear()] + wizard._get_line_vals(wizard.mo_ids, datetime.combine(wizard.date, time.max))

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
