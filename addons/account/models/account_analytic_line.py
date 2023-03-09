# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    invoice_count = fields.Integer("Invoice Count", compute='_compute_invoice_count')
    vendor_bill_count = fields.Integer("Vendor Bill Count", compute='_compute_vendor_bill_count')

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

    @api.depends('line_ids')
    def _compute_invoice_count(self):
        sale_types = self.env['account.move'].get_sale_types()
        domain = [
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', 'in', sale_types),
            ('analytic_account_id', 'in', self.ids)
        ]
        groups = self.env['account.move.line'].read_group(domain, ['move_id:count_distinct'], ['analytic_account_id'])
        moves_count_mapping = dict((g['analytic_account_id'][0], g['move_id']) for g in groups)
        for account in self:
            account.invoice_count = moves_count_mapping.get(account.id, 0)

    @api.depends('line_ids')
    def _compute_vendor_bill_count(self):
        purchase_types = self.env['account.move'].get_purchase_types()
        domain = [
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type', 'in', purchase_types),
            ('analytic_account_id', 'in', self.ids)
        ]
        groups = self.env['account.move.line'].read_group(domain, ['move_id:count_distinct'], ['analytic_account_id'])
        moves_count_mapping = dict((g['analytic_account_id'][0], g['move_id']) for g in groups)
        for account in self:
            account.vendor_bill_count = moves_count_mapping.get(account.id, 0)

    def action_view_invoice(self):
        self.ensure_one()
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', self.line_ids.move_id.move_id.ids), ('move_type', 'in', self.env['account.move'].get_sale_types())],
            "context": {"create": False},
            "name": _("Customer Invoices"),
            'view_mode': 'tree,form',
        }
        return result

    def action_view_vendor_bill(self):
        self.ensure_one()
        result = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "domain": [('id', 'in', self.line_ids.move_id.move_id.ids), ('move_type', 'in', self.env['account.move'].get_purchase_types())],
            "context": {"create": False},
            "name": _("Vendor Bills"),
            'view_mode': 'tree,form',
        }
        return result

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
    general_account_id = fields.Many2one('account.account', string='Financial Account', ondelete='restrict', readonly=True,
                                         related='move_id.account_id', store=True, domain="[('deprecated', '=', False), ('company_id', '=', company_id)]",
                                         compute_sudo=True)
    move_id = fields.Many2one('account.move.line', string='Journal Item', ondelete='cascade', index=True, check_company=True)
    code = fields.Char(size=8)
    ref = fields.Char(string='Ref.')
    category = fields.Selection(selection_add=[('invoice', 'Customer Invoice'), ('vendor_bill', 'Vendor Bill')])

    @api.onchange('product_id', 'product_uom_id', 'unit_amount', 'currency_id')
    def on_change_unit_amount(self):
        if not self.product_id:
            return {}

        result = 0.0
        prod_accounts = self.product_id.product_tmpl_id.with_company(self.company_id)._get_product_accounts()
        unit = self.product_uom_id
        account = prod_accounts['expense']
        if not unit or self.product_id.uom_po_id.category_id.id != unit.category_id.id:
            unit = self.product_id.uom_po_id

        # Compute based on pricetype
        amount_unit = self.product_id.price_compute('standard_price', uom=unit)[self.product_id.id]
        amount = amount_unit * self.unit_amount or 0.0
        result = (self.currency_id.round(amount) if self.currency_id else round(amount, 2)) * -1
        self.amount = result
        self.general_account_id = account
        self.product_uom_id = unit

    @api.model
    def view_header_get(self, view_id, view_type):
        if self.env.context.get('account_id'):
            return _(
                "Entries: %(account)s",
                account=self.env['account.analytic.account'].browse(self.env.context['account_id']).name
            )
        return super().view_header_get(view_id, view_type)
