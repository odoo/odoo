# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    @api.constrains('company_id')
    def _check_company_consistency(self):
        analytic_accounts = self.filtered('company_id')

        if not analytic_accounts:
            return

        self.flush(['company_id'])
        self._cr.execute('''
            SELECT line.id
            FROM account_move_line line
            JOIN account_analytic_account account ON account.id = line.analytic_account_id
            WHERE line.analytic_account_id IN %s
            AND line.company_id != account.company_id
        ''', [tuple(analytic_accounts.ids)])

        if self._cr.fetchone():
            raise UserError(_("You can't set a different company on your analytic account since there are some journal items linked to it."))


class AccountAnalyticTag(models.Model):
    _inherit = 'account.analytic.tag'

    @api.constrains('company_id')
    def _check_company_consistency(self):
        analytic_tags = self.filtered('company_id')

        if not analytic_tags:
            return

        self.flush(['company_id'])
        self._cr.execute('''
            SELECT line.id
            FROM account_analytic_tag_account_move_line_rel tag_rel
            JOIN account_analytic_tag tag ON tag.id = tag_rel.account_analytic_tag_id
            JOIN account_move_line line ON line.id = tag_rel.account_move_line_id
            WHERE tag_rel.account_analytic_tag_id IN %s
            AND line.company_id != tag.company_id
        ''', [tuple(analytic_tags.ids)])

        if self._cr.fetchone():
            raise UserError(_("You can't set a different company on your analytic tags since there are some journal items linked to it."))


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'
    _description = 'Analytic Line'

    product_id = fields.Many2one('product.product', string='Product', check_company=True)
    general_account_id = fields.Many2one(
        'account.account', string='Financial Account', ondelete='restrict', readonly=False,
        related='move_id.account_id', store=True, compute='_compute_general_account_id',
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]", compute_sudo=True)
    move_id = fields.Many2one('account.move.line', string='Journal Item', ondelete='cascade', index=True, check_company=True)
    code = fields.Char(size=8)
    ref = fields.Char(string='Ref.')

    amount = fields.Monetary(compute='_compute_unit_amount', store=True, readonly=False)
    product_uom_id = fields.Many2one(compute='_compute_product_uom_id', store=True, readonly=False)

    @api.depends('product_id', 'company_id')
    def _compute_general_account_id(self):
        for line in self:
            if not line.product_id:
                continue
            prod_accounts = line.product_id.product_tmpl_id.with_company(line.company_id)._get_product_accounts()
            line.general_account_id = prod_accounts['expense']

    @api.depends('product_id', 'product_uom_id')
    def _compute_product_uom_id(self):
        for line in self:
            if not line.product_id:
                continue
            unit = line.product_uom_id
            if not unit or line.product_id.uom_po_id.category_id.id != unit.category_id.id:
                line.product_uom_id = line.product_id.uom_po_id

    @api.depends('product_id', 'product_uom_id', 'unit_amount', 'currency_id')
    def _compute_amount(self):
        for line in self:
            if not line.product_id:
                continue

            unit = line.product_uom_id
            if not unit or line.product_id.uom_po_id.category_id.id != unit.category_id.id:
                unit = line.product_id.uom_po_id

            # Compute based on pricetype
            amount_unit = line.product_id.price_compute('standard_price', uom=unit)[line.product_id.id]
            amount = amount_unit * line.unit_amount or 0.0
            result = (line.currency_id.round(amount) if line.currency_id else round(amount, 2)) * -1
            line.amount = result

    @api.model
    def view_header_get(self, view_id, view_type):
        if self.env.context.get('account_id'):
            return _(
                "Entries: %(account)s",
                account=self.env['account.analytic.account'].browse(self.env.context['account_id']).name
            )
        return super().view_header_get(view_id, view_type)
