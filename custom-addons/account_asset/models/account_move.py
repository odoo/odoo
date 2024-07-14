# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, _lt, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
from odoo.tools.misc import formatLang
from collections import defaultdict, namedtuple
from dateutil.relativedelta import relativedelta


class AccountMove(models.Model):
    _inherit = 'account.move'

    asset_id = fields.Many2one('account.asset', string='Asset', index=True, ondelete='cascade', copy=False, domain="[('company_id', '=', company_id)]")
    asset_remaining_value = fields.Monetary(string='Depreciable Value', compute='_compute_depreciation_cumulative_value')
    asset_depreciated_value = fields.Monetary(string='Cumulative Depreciation', compute='_compute_depreciation_cumulative_value')
    # true when this move is the result of the changing of value of an asset
    asset_value_change = fields.Boolean()
    #  how many days of depreciation this entry corresponds to
    asset_number_days = fields.Integer(string="Number of days", copy=False) # deprecated
    asset_depreciation_beginning_date = fields.Date(string="Date of the beginning of the depreciation", copy=False) # technical field stating when the depreciation associated with this entry has begun
    depreciation_value = fields.Monetary(
        string="Depreciation",
        compute="_compute_depreciation_value", inverse="_inverse_depreciation_value", store=True,
    )

    asset_ids = fields.One2many('account.asset', string='Assets', compute="_compute_asset_ids")
    asset_id_display_name = fields.Char(compute="_compute_asset_ids")   # just a button label. That's to avoid a plethora of different buttons defined in xml
    count_asset = fields.Integer(compute="_compute_asset_ids")
    draft_asset_exists = fields.Boolean(compute="_compute_asset_ids")

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    @api.depends('asset_id', 'depreciation_value', 'asset_id.total_depreciable_value', 'asset_id.already_depreciated_amount_import')
    def _compute_depreciation_cumulative_value(self):
        self.asset_depreciated_value = 0
        self.asset_remaining_value = 0

        # make sure to protect all the records being assigned, because the
        # assignments invoke method write() on non-protected records, which may
        # cause an infinite recursion in case method write() needs to read one
        # of these fields (like in case of a base automation)
        fields = [self._fields['asset_remaining_value'], self._fields['asset_depreciated_value']]
        with self.env.protecting(fields, self.asset_id.depreciation_move_ids):
            for asset in self.asset_id:
                depreciated = 0
                remaining = asset.total_depreciable_value - asset.already_depreciated_amount_import
                for move in asset.depreciation_move_ids.sorted(lambda mv: (mv.date, mv._origin.id)):
                    remaining -= move.depreciation_value
                    depreciated += move.depreciation_value
                    move.asset_remaining_value = remaining
                    move.asset_depreciated_value = depreciated

    @api.depends('line_ids.balance')
    def _compute_depreciation_value(self):
        for move in self:
            asset = move.asset_id or move.reversed_entry_id.asset_id  # reversed moves are created before being assigned to the asset
            if asset:
                account_internal_group = 'expense'
                asset_depreciation = sum(
                    move.line_ids.filtered(lambda l: l.account_id.internal_group == account_internal_group or l.account_id == asset.account_depreciation_expense_id).mapped('balance')
                )
                # Special case of closing entry - only disposed assets of type 'purchase' should match this condition
                # The condition on len(move.line_ids) is to avoid the case where there is only one depreciation move, and it is not a disposal move
                # The condition will be matched because a disposal move from a disposal move will always have more than 2 lines, unlike a normal depreciation move
                if any(
                    line.account_id == asset.account_asset_id
                    and float_compare(-line.balance, asset.original_value, precision_rounding=asset.currency_id.rounding) == 0
                    for line in move.line_ids
                ) and len(move.line_ids) > 2:
                    asset_depreciation = (
                        asset.original_value
                        - asset.salvage_value
                        - (
                            move.line_ids[1].debit if asset.original_value > 0 else move.line_ids[1].credit
                        ) * (-1 if asset.original_value < 0 else 1)
                    )
            else:
                asset_depreciation = 0
            move.depreciation_value = asset_depreciation

    # -------------------------------------------------------------------------
    # INVERSE METHODS
    # -------------------------------------------------------------------------
    def _inverse_depreciation_value(self):
        for move in self:
            asset = move.asset_id
            amount = abs(move.depreciation_value)
            account = asset.account_depreciation_expense_id
            move.write({'line_ids': [
                Command.update(line.id, {
                    'balance': amount if line.account_id == account else -amount,
                })
                for line in move.line_ids
            ]})

    # -------------------------------------------------------------------------
    # CONSTRAINT METHODS
    # -------------------------------------------------------------------------
    @api.constrains('state', 'asset_id')
    def _constrains_check_asset_state(self):
        for move in self.filtered(lambda mv: mv.asset_id):
            asset_id = move.asset_id
            if asset_id.state == 'draft' and move.state == 'posted':
                raise ValidationError(_("You can't post an entry related to a draft asset. Please post the asset before."))

    def _post(self, soft=True):
        # OVERRIDE
        posted = super()._post(soft)

        # log the post of a depreciation
        posted._log_depreciation_asset()

        # look for any asset to create, in case we just posted a bill on an account
        # configured to automatically create assets
        posted.sudo()._auto_create_asset()

        return posted

    def _reverse_moves(self, default_values_list=None, cancel=False):
        if default_values_list is None:
            default_values_list = [{} for _i in self]
        for move, default_values in zip(self, default_values_list):
            # Report the value of this move to the next draft move or create a new one
            if move.asset_id:
                # Recompute the status of the asset for all depreciations posted after the reversed entry

                first_draft = min(move.asset_id.depreciation_move_ids.filtered(lambda m: m.state == 'draft'), key=lambda m: m.date, default=None)
                if first_draft:
                    # If there is a draft, simply move/add the depreciation amount here
                    first_draft.depreciation_value += move.depreciation_value
                else:
                    # If there was no draft move left, create one
                    last_date = max(move.asset_id.depreciation_move_ids.mapped('date'))
                    method_period = move.asset_id.method_period

                    self.create(self._prepare_move_for_asset_depreciation({
                        'asset_id': move.asset_id,
                        'amount': move.depreciation_value,
                        'depreciation_beginning_date': last_date + (relativedelta(months=1) if method_period == "1" else relativedelta(years=1)),
                        'date': last_date + (relativedelta(months=1) if method_period == "1" else relativedelta(years=1)),
                        'asset_number_days': 0
                    }))

                msg = _('Depreciation entry %s reversed (%s)', move.name, formatLang(self.env, move.depreciation_value, currency_obj=move.company_id.currency_id))
                move.asset_id.message_post(body=msg)
                default_values['asset_id'] = move.asset_id.id
                default_values['asset_number_days'] = -move.asset_number_days
                default_values['asset_depreciation_beginning_date'] = default_values.get('date', move.date)

        return super(AccountMove, self)._reverse_moves(default_values_list, cancel)

    def button_cancel(self):
        # OVERRIDE
        res = super(AccountMove, self).button_cancel()
        self.env['account.asset'].sudo().search([('original_move_line_ids.move_id', 'in', self.ids)]).write({'active': False})
        return res

    def button_draft(self):
        for move in self:
            if any(asset_id.state != 'draft' for asset_id in move.asset_ids):
                raise UserError(_('You cannot reset to draft an entry related to a posted asset'))
            # Remove any draft asset that could be linked to the account move being reset to draft
            move.asset_ids.filtered(lambda x: x.state == 'draft').unlink()
        return super(AccountMove, self).button_draft()

    def _log_depreciation_asset(self):
        for move in self.filtered(lambda m: m.asset_id):
            asset = move.asset_id
            msg = _('Depreciation entry %s posted (%s)', move.name, formatLang(self.env, move.depreciation_value, currency_obj=move.company_id.currency_id))
            asset.message_post(body=msg)

    def _auto_create_asset(self):
        create_list = []
        invoice_list = []
        auto_validate = []
        for move in self:
            if not move.is_invoice():
                continue

            for move_line in move.line_ids:
                if (
                    move_line.account_id
                    and (move_line.account_id.can_create_asset)
                    and move_line.account_id.create_asset != "no"
                    and not (move_line.currency_id or move.currency_id).is_zero(move_line.price_total)
                    and not move_line.asset_ids
                    and not move_line.tax_line_id
                    and move_line.price_total > 0
                    and not (move.move_type in ('out_invoice', 'out_refund') and move_line.account_id.internal_group == 'asset')
                ):
                    if not move_line.name:
                        raise UserError(_('Journal Items of %(account)s should have a label in order to generate an asset', account=move_line.account_id.display_name))
                    if move_line.account_id.multiple_assets_per_line:
                        # decimal quantities are not supported, quantities are rounded to the lower int
                        units_quantity = max(1, int(move_line.quantity))
                    else:
                        units_quantity = 1
                    vals = {
                        'name': move_line.name,
                        'company_id': move_line.company_id.id,
                        'currency_id': move_line.company_currency_id.id,
                        'analytic_distribution': move_line.analytic_distribution,
                        'original_move_line_ids': [(6, False, move_line.ids)],
                        'state': 'draft',
                        'acquisition_date': move.invoice_date if not move.reversed_entry_id else move.reversed_entry_id.invoice_date,
                    }
                    model_id = move_line.account_id.asset_model
                    if model_id:
                        vals.update({
                            'model_id': model_id.id,
                        })
                    auto_validate.extend([move_line.account_id.create_asset == 'validate'] * units_quantity)
                    invoice_list.extend([move] * units_quantity)
                    for i in range(1, units_quantity + 1):
                        if units_quantity > 1:
                            vals['name'] = move_line.name + _(" (%s of %s)", i, units_quantity)
                        create_list.extend([vals.copy()])

        assets = self.env['account.asset'].with_context({}).create(create_list)
        for asset, vals, invoice, validate in zip(assets, create_list, invoice_list, auto_validate):
            if 'model_id' in vals:
                asset._onchange_model_id()
                if validate:
                    asset.validate()
            if invoice:
                asset.message_post(body=_('Asset created from invoice: %s', invoice._get_html_link()))
                asset._post_non_deductible_tax_value()
        return assets

    @api.model
    def _prepare_move_for_asset_depreciation(self, vals):
        missing_fields = {'asset_id', 'amount', 'depreciation_beginning_date', 'date', 'asset_number_days'} - set(vals)
        if missing_fields:
            raise UserError(_('Some fields are missing %s', ', '.join(missing_fields)))
        asset = vals['asset_id']
        analytic_distribution = asset.analytic_distribution
        depreciation_date = vals.get('date', fields.Date.context_today(self))
        company_currency = asset.company_id.currency_id
        current_currency = asset.currency_id
        prec = company_currency.decimal_places
        amount_currency = vals['amount']
        amount = current_currency._convert(amount_currency, company_currency, asset.company_id, depreciation_date)
        # Keep the partner on the original invoice if there is only one
        partner = asset.original_move_line_ids.mapped('partner_id')
        partner = partner[:1] if len(partner) <= 1 else self.env['res.partner']
        move_line_1 = {
            'name': asset.name,
            'partner_id': partner.id,
            'account_id': asset.account_depreciation_id.id,
            'debit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
            'credit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
            'analytic_distribution': analytic_distribution,
            'currency_id': current_currency.id,
            'amount_currency': -amount_currency,
        }
        move_line_2 = {
            'name': asset.name,
            'partner_id': partner.id,
            'account_id': asset.account_depreciation_expense_id.id,
            'credit': 0.0 if float_compare(amount, 0.0, precision_digits=prec) > 0 else -amount,
            'debit': amount if float_compare(amount, 0.0, precision_digits=prec) > 0 else 0.0,
            'analytic_distribution': analytic_distribution,
            'currency_id': current_currency.id,
            'amount_currency': amount_currency,
        }
        move_vals = {
            'partner_id': partner.id,
            'date': depreciation_date,
            'journal_id': asset.journal_id.id,
            'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
            'asset_id': asset.id,
            'ref': _("%s: Depreciation", asset.name),
            'asset_depreciation_beginning_date': vals['depreciation_beginning_date'],
            'asset_number_days': vals['asset_number_days'],
            'name': '/',
            'asset_value_change': vals.get('asset_value_change', False),
            'move_type': 'entry',
            'currency_id': current_currency.id,
        }
        return move_vals

    @api.depends('line_ids.asset_ids')
    def _compute_asset_ids(self):
        for record in self:
            record.asset_ids = record.line_ids.asset_ids
            record.count_asset = len(record.asset_ids)
            record.asset_id_display_name = _('Asset')
            record.draft_asset_exists = bool(record.asset_ids.filtered(lambda x: x.state == "draft"))

    def open_asset_view(self):
        return self.asset_id.open_asset(['form'])

    def action_open_asset_ids(self):
        return self.asset_ids.open_asset(['tree', 'form'])


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    asset_ids = fields.Many2many('account.asset', 'asset_move_line_rel', 'line_id', 'asset_id', string='Related Assets', copy=False)
    non_deductible_tax_value = fields.Monetary(compute='_compute_non_deductible_tax_value', currency_field='company_currency_id')

    def _get_computed_taxes(self):
        if self.move_id.asset_id:
            return self.tax_ids
        return super()._get_computed_taxes()

    def turn_as_asset(self):
        ctx = self.env.context.copy()
        ctx.update({
            'default_original_move_line_ids': [(6, False, self.env.context['active_ids'])],
            'default_company_id': self.company_id.id,
        })
        if any(line.move_id.state == 'draft' for line in self):
            raise UserError(_("All the lines should be posted"))
        if any(account != self[0].account_id for account in self.mapped('account_id')):
            raise UserError(_("All the lines should be from the same account"))
        return {
            "name": _("Turn as an asset"),
            "type": "ir.actions.act_window",
            "res_model": "account.asset",
            "views": [[False, "form"]],
            "target": "current",
            "context": ctx,
        }

    @api.depends('tax_ids.invoice_repartition_line_ids')
    def _compute_non_deductible_tax_value(self):
        """ Handle the specific case of non deductible taxes,
        such as "50% Non Déductible - Frais de voiture (Prix Excl.)" in Belgium.
        """
        non_deductible_tax_ids = self.tax_ids.invoice_repartition_line_ids.filtered(
            lambda line: line.repartition_type == 'tax' and not line.use_in_tax_closing
        ).tax_id

        res = {}
        if non_deductible_tax_ids:
            domain = [('move_id', 'in', self.move_id.ids)]
            tax_details_query, tax_details_params = self._get_query_tax_details_from_domain(domain)

            self.flush_model()
            self._cr.execute(f'''
                SELECT
                    tdq.base_line_id,
                    SUM(tdq.tax_amount_currency)
                FROM ({tax_details_query}) AS tdq
                JOIN account_move_line aml ON aml.id = tdq.tax_line_id
                JOIN account_tax_repartition_line trl ON trl.id = tdq.tax_repartition_line_id
                WHERE tdq.base_line_id IN %s
                AND trl.use_in_tax_closing IS FALSE
                GROUP BY tdq.base_line_id
            ''', tax_details_params + [tuple(self.ids)])

            res = {row['base_line_id']: row['sum'] for row in self._cr.dictfetchall()}

        for record in self:
            record.non_deductible_tax_value = res.get(record._origin.id, 0.0)
