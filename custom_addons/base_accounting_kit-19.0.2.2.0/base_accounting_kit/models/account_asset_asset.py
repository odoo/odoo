# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
import calendar
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.fields import Date
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF, float_is_zero
from odoo.exceptions import UserError, ValidationError


class AccountAssetAsset(models.Model):
    """
        Model for managing assets with depreciation functionality
    """
    _name = 'account.asset.asset'
    _description = 'Asset/Revenue Recognition'
    _inherit = ['mail.thread']

    entry_count = fields.Integer(compute='_entry_count',
                                 string='# Asset Entries')
    name = fields.Char(string='Asset Name', required=True)
    code = fields.Char(string='Reference', size=32)
    value = fields.Float(string='Gross Value', required=True,
                         digits=0)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  required=True,
                                  default=lambda self: self.env.company.currency_id.id)
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True,
                                 default=lambda self: self.env.company)
    note = fields.Text()
    category_id = fields.Many2one('account.asset.category', string='Asset Model',
                                  required=False, change_default=True
                                  )
    date = fields.Date(string='Date', required=True,
                       default=fields.Date.context_today)
    state = fields.Selection(
        [('draft', 'Draft'), ('open', 'Running'), ('close', 'Close'),('cancelled','Cancelled')],
        'Status', required=True, copy=False, default='draft',
        help="When an asset is created, the status is 'Draft'.\n"
             "If the asset is confirmed, the status goes in 'Running' and the depreciation lines can be posted in the accounting.\n"
             "You can manually close an asset when the depreciation is over. If the last line of depreciation is posted, the asset automatically goes in that status.")
    active = fields.Boolean(default=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    method = fields.Selection(
        [('linear', 'Straight Line'), ('degressive', 'Declining')],
        string='Computation Method', required=True,default='linear',
        help="Choose the method to use to compute the amount of depreciation lines.\n  * Linear: Calculated on basis of: Gross Value / Number of Depreciations\n"
             "  * Degressive: Calculated on basis of: Residual Value * Degressive Factor")
    method_number = fields.Integer(string='Number of Depreciations',
                                   default=5,
                                   help="The number of depreciation's needed to depreciate your asset")
    method_period = fields.Integer(string='Number of Months in a Period',
                                   required=True, default=12,
                                   help="The amount of time between two depreciation's, in months")
    method_end = fields.Date(string='Ending Date')
    method_progress_factor = fields.Float(string='Degressive Factor',
                                          default=0.3,)
    value_residual = fields.Float(compute='_amount_residual',
                                  digits=0, string='Residual Value')
    method_time = fields.Selection(
        [('number', 'Number of Entries'), ('end', 'Ending Date')],
        string='Time Method', required=True,  default='number',
        help="Choose the method to use to compute the dates and number of entries.\n"
             "  * Number of Entries: Fix the number of entries and the time between 2 depreciations.\n"
             "  * Ending Date: Choose the time between 2 depreciations and the date the depreciations won't go beyond.")
    prorata = fields.Boolean(string='Prorata Temporis',
                             help='Indicates that the first depreciation entry for this asset have to be done from the purchase date instead of the first January / Start date of fiscal year')
    depreciation_line_ids = fields.One2many('account.asset.depreciation.line',
                                            'asset_id',
                                            string='Depreciation Lines',
                                            )
    salvage_value = fields.Float(string='Salvage Value', digits=0,

                                 help="It is the amount you plan to have that you cannot depreciate.")
    invoice_id = fields.Many2one('account.move', string='Invoice',
                                 copy=False)
    type = fields.Selection([('sale', 'Sale: Revenue Recognition'),
                             ('purchase', 'Purchase: Asset')], required=True, index=True, default='purchase')


    #asset category
    account_analytic_id = fields.Many2one('account.analytic.account',
                                          string='Analytic Account',
                                          domain="[('company_id', '=', company_id)]")
    account_asset_id = fields.Many2one('account.account',
                                       string='Asset Account', required=True,
                                       domain="[('account_type', '!=', 'asset_receivable'),('account_type', '!=', 'liability_payable'),('account_type', '!=', 'asset_cash'),('account_type', '!=', 'liability_credit_card'),('active', '=', True)]",
                                       help="Account used to record the purchase of the asset at its original price.")
    account_depreciation_id = fields.Many2one(
        'account.account', string='Depreciation Account',
        required=True,
        domain="[('account_type', '!=', 'asset_receivable'),('account_type', '!=', 'liability_payable'),('account_type', '!=', 'asset_cash'),('account_type', '!=', 'liability_credit_card'),('active', '=', True)]",
        help="Account used in the depreciation entries, to decrease the asset value.")
    account_depreciation_expense_id = fields.Many2one(
        'account.account', string='Expense Account',
        required=True,
        domain="[('account_type', '!=', 'asset_receivable'),('account_type', '!=','liability_payable'),('account_type', '!=', 'asset_cash'),('account_type', '!=','liability_credit_card'),('active', '=', True)]",
        help="Account used in the periodical entries, to record a part of the asset as expense.")
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 required=True)
    open_asset = fields.Boolean(string='Auto-confirm Assets',
                                help="Check this if you want to automatically confirm the assets of this category when created by invoices.")
    group_entries = fields.Boolean(string='Group Journal Entries',
                                   help="Check this if you want to group the generated entries by categories.")

    def unlink(self):
        """ Prevents deletion of assets in 'open' or 'close' state or with posted depreciation entries."""
        for asset in self:
            if asset.state in ['open', 'close']:
                raise UserError(
                    _('You cannot delete a document is in %s state.') % (
                        asset.state,))
            for depreciation_line in asset.depreciation_line_ids:
                if depreciation_line.move_id:
                    raise UserError(_(
                        'You cannot delete a document that contains posted entries.'))
        return super(AccountAssetAsset, self).unlink()

    def _get_last_depreciation_date(self):
        """
        @param id: ids of a account.asset.asset objects
        @return: Returns a dictionary of the effective dates of the last depreciation entry made for given asset ids. If there isn't any, return the purchase date of this asset
        """
        self.env.cr.execute("""
            SELECT a.id as id, COALESCE(MAX(m.date),a.date) AS date
            FROM account_asset_asset a
            LEFT JOIN account_asset_depreciation_line rel ON (rel.asset_id = a.id)
            LEFT JOIN account_move m ON (rel.move_id = m.id)
            WHERE a.id IN %s
            GROUP BY a.id, m.date """, (tuple(self.ids),))
        result = dict(self.env.cr.fetchall())
        return result

    @api.onchange('category_id')
    def gross_value(self):
        """Update the 'value' field based on the 'price' of the selected 'category_id'."""
        self.value = self.category_id.price
    @api.onchange('method')
    def onchange_method(self):
        if self.depreciation_line_ids:
            self.depreciation_line_ids = [(fields.Command.clear())]


    @api.model
    def compute_generated_entries(self, date, asset_type=None):
        """Compute generated entries for assets based on the provided date and asset type."""
        # Entries generated : one by grouped category and one by asset from ungrouped category
        created_move_ids = []
        type_domain = []
        if asset_type:
            type_domain = [('type', '=', asset_type)]

        ungrouped_assets = self.env['account.asset.asset'].search(
            type_domain + [('state', '=', 'open'),
                           ('category_id.group_entries', '=', False)])
        created_move_ids += ungrouped_assets._compute_entries(date,
                                                              group_entries=False)

        for grouped_category in self.env['account.asset.category'].search(
                type_domain + [('group_entries', '=', True)]):
            assets = self.env['account.asset.asset'].search(
                [('state', '=', 'open'),
                 ('category_id', '=', grouped_category.id)])
            created_move_ids += assets._compute_entries(date,
                                                        group_entries=True)
        return created_move_ids

    def _compute_board_amount(self, sequence, residual_amount, amount_to_depr,
                              undone_dotation_number,
                              posted_depreciation_line_ids, total_days,
                              depreciation_date):
        """Compute the depreciation amount for a specific sequence in the asset's depreciation schedule."""
        amount = 0
        if sequence == undone_dotation_number:
            amount = residual_amount
        else:
            if self.method == 'linear':
                amount = amount_to_depr / (undone_dotation_number - len(
                    posted_depreciation_line_ids))
                if self.prorata:
                    amount = amount_to_depr / self.method_number
                    if sequence == 1:
                        if self.method_period % 12 != 0:
                            date = datetime.strptime(str(self.date),
                                                     '%Y-%m-%d')
                            month_days = \
                                calendar.monthrange(date.year, date.month)[1]
                            days = month_days - date.day + 1
                            amount = (
                                             amount_to_depr / self.method_number) / month_days * days
                        else:
                            days = (self.company_id.compute_fiscalyear_dates(
                                depreciation_date)[
                                        'date_to'] - depreciation_date).days + 1
                            amount = (
                                             amount_to_depr / self.method_number) / total_days * days
            elif self.method == 'degressive':
                amount = residual_amount * self.method_progress_factor
                if self.prorata:
                    if sequence == 1:
                        if self.method_period % 12 != 0:
                            date = datetime.strptime(str(self.date),
                                                     '%Y-%m-%d')
                            month_days = \
                                calendar.monthrange(date.year, date.month)[1]
                            days = month_days - date.day + 1
                            amount = (
                                             residual_amount * self.method_progress_factor) / month_days * days
                        else:
                            days = (self.company_id.compute_fiscalyear_dates(
                                depreciation_date)[
                                        'date_to'] - depreciation_date).days + 1
                            amount = (
                                             residual_amount * self.method_progress_factor) / total_days * days
        return amount

    def _compute_board_undone_dotation_nb(self, depreciation_date, total_days):
        """Compute the number of remaining depreciations for an asset based on the depreciation date and total days."""
        undone_dotation_number = self.method_number
        if self.method_time == 'end':
            end_date = datetime.strptime(str(self.method_end), DF).date()
            undone_dotation_number = 0
            while depreciation_date <= end_date:
                depreciation_date = date(depreciation_date.year,
                                         depreciation_date.month,
                                         depreciation_date.day) + relativedelta(
                    months=+self.method_period)
                undone_dotation_number += 1
        if self.prorata:
            undone_dotation_number += 1
        return undone_dotation_number

    def compute_depreciation_board(self):
        """
            Compute the depreciation schedule for the asset based on its current state and parameters.
            This method calculates the depreciation amount for each period and generates depreciation entries accordingly.
        """
        self.ensure_one()
        posted_depreciation_line_ids = self.depreciation_line_ids.filtered(
            lambda x: x.move_check).sorted(key=lambda l: l.depreciation_date)
        unposted_depreciation_line_ids = self.depreciation_line_ids.filtered(
            lambda x: not x.move_check)

        # Remove old unposted depreciation lines. We cannot use unlink() with One2many field
        commands = [(2, line_id.id, False) for line_id in
                    unposted_depreciation_line_ids]

        if self.value_residual != 0.0:
            amount_to_depr = residual_amount = self.value_residual
            if self.prorata:
                # if we already have some previous validated entries, starting date is last entry + method perio
                if posted_depreciation_line_ids and \
                        posted_depreciation_line_ids[-1].depreciation_date:
                    last_depreciation_date = datetime.strptime(
                        posted_depreciation_line_ids[-1].depreciation_date,
                        DF).date()
                    depreciation_date = last_depreciation_date + relativedelta(
                        months=+self.method_period)
                else:
                    depreciation_date = datetime.strptime(
                        str(self._get_last_depreciation_date()[self.id]),
                        DF).date()
            else:
                # depreciation_date = 1st of January of purchase year if annual valuation, 1st of
                # purchase month in other cases
                if self.method_period >= 12:
                    if self.company_id.fiscalyear_last_month:
                        asset_date = date(year=int(self.date.year),
                                          month=int(
                                              self.company_id.fiscalyear_last_month),
                                          day=int(
                                              self.company_id.fiscalyear_last_day)) + relativedelta(
                            days=1) + \
                                     relativedelta(year=int(
                                         self.date.year))  # e.g. 2018-12-31 +1 -> 2019
                    else:
                        asset_date = datetime.strptime(
                            str(self.date)[:4] + '-01-01', DF).date()
                else:
                    asset_date = datetime.strptime(str(self.date)[:7] + '-01',
                                                   DF).date()
                # if we already have some previous validated entries, starting date isn't 1st January but last entry + method period
                if posted_depreciation_line_ids and \
                        posted_depreciation_line_ids[-1].depreciation_date:
                    last_depreciation_date = datetime.strptime(str(
                        posted_depreciation_line_ids[-1].depreciation_date),
                        DF).date()
                    depreciation_date = last_depreciation_date + relativedelta(
                        months=+self.method_period)
                else:
                    depreciation_date = asset_date
            day = depreciation_date.day
            month = depreciation_date.month
            year = depreciation_date.year
            total_days = (year % 4) and 365 or 366

            undone_dotation_number = self._compute_board_undone_dotation_nb(
                depreciation_date, total_days)

            for x in range(len(posted_depreciation_line_ids),
                           undone_dotation_number):
                sequence = x + 1
                amount = self._compute_board_amount(sequence, residual_amount,
                                                    amount_to_depr,
                                                    undone_dotation_number,
                                                    posted_depreciation_line_ids,
                                                    total_days,
                                                    depreciation_date)

                amount = self.currency_id.round(amount)
                if float_is_zero(amount,
                                 precision_rounding=self.currency_id.rounding):
                    continue
                residual_amount -= amount
                vals = {
                    'amount': amount,
                    'asset_id': self.id,
                    'sequence': sequence,
                    'name': (self.code or '') + '/' + str(sequence),
                    'remaining_value': residual_amount if residual_amount >= 0 else 0.0,
                    'depreciated_value': self.value - (
                            self.salvage_value + residual_amount),
                    'depreciation_date': depreciation_date.strftime(DF),
                }
                commands.append((0, False, vals))
                # Considering Depr. Period as months
                depreciation_date = date(year, month, day) + relativedelta(
                    months=+self.method_period)
                day = depreciation_date.day
                month = depreciation_date.month
                year = depreciation_date.year

        self.write({'depreciation_line_ids': commands})
        last_depr_date = None
        if self.depreciation_line_ids:
            last_depr_date = max(self.depreciation_line_ids.mapped('depreciation_date'))
        if last_depr_date:
            self._compute_entries(date=last_depr_date)
        return True

    def validate(self):
        """Update the state to 'open' and track specific fields based on the asset's method."""
        self.write({'state': 'open'})
        field = [
            'method',
            'method_number',
            'method_period',
            'method_end',
            'method_progress_factor',
            'method_time',
            'salvage_value',
            'invoice_id',
        ]
        ref_tracked_fields = self.env['account.asset.asset'].fields_get(field)
        if not self.depreciation_line_ids:
            self.compute_depreciation_board()
        for asset in self:
            tracked_fields = ref_tracked_fields.copy()
            if asset.method == 'linear':
                del (tracked_fields['method_progress_factor'])
            if asset.method_time != 'end':
                del (tracked_fields['method_end'])
            else:
                del (tracked_fields['method_number'])
            dummy, tracking_value_ids = asset._mail_track(tracked_fields,
                                                          dict.fromkeys(
                                                              field))
            asset.message_post(subject=_('Asset created'),
                               tracking_value_ids=tracking_value_ids)

            today_date = fields.Date.context_today(self)

            # Split lines based on depreciation_date
            draft_lines = asset.depreciation_line_ids.filtered(lambda l: l.move_id and l.move_id.state == 'draft')

            #Post only entries before today
            lines_to_post_now = draft_lines.filtered(lambda l: l.depreciation_date < today_date)
            moves_to_post_now = lines_to_post_now.mapped('move_id')
            if moves_to_post_now:
                moves_to_post_now._post()

            #Set auto_post='at_date' for entries today or later
            future_lines = draft_lines.filtered(lambda l: l.depreciation_date >= today_date)
            future_moves = future_lines.mapped('move_id')
            if future_moves:
                future_moves.write({'auto_post': 'at_date'})

        return True


    def _get_disposal_moves(self):
        """Get the disposal moves for the asset."""
        move_ids = []
        for asset in self:
            unposted_depreciation_line_ids = asset.depreciation_line_ids.filtered(
                lambda x: not x.move_check)
            if unposted_depreciation_line_ids:
                old_values = {
                    'method_end': asset.method_end,
                    'method_number': asset.method_number,
                }

                # Remove all unposted depr. lines
                commands = [(2, line_id.id, False) for line_id in
                            unposted_depreciation_line_ids]

                # Create a new depr. line with the residual amount and post it
                sequence = len(asset.depreciation_line_ids) - len(
                    unposted_depreciation_line_ids) + 1
                today = datetime.today().strftime(DF)
                vals = {
                    'amount': asset.value_residual,
                    'asset_id': asset.id,
                    'sequence': sequence,
                    'name': (asset.code or '') + '/' + str(sequence),
                    'remaining_value': 0,
                    'depreciated_value': asset.value - asset.salvage_value,
                    # the asset is completely depreciated
                    'depreciation_date': today,
                }
                commands.append((0, False, vals))
                asset.write(
                    {'depreciation_line_ids': commands, 'method_end': today,
                     'method_number': sequence})
                tracked_fields = self.env['account.asset.asset'].fields_get(
                    ['method_number', 'method_end'])
                changes, tracking_value_ids = asset._mail_track(
                    tracked_fields, old_values)

                if changes:
                    asset.message_post(subject=_(
                        'Asset sold or disposed. Accounting entry awaiting for validation.'),
                        tracking_value_ids=tracking_value_ids)
                move_ids += asset.depreciation_line_ids[-1].create_move(
                    post_move=False)

        return move_ids

    def set_to_close(self):
        """Set the asset to close state by creating disposal moves and returning an action window to view the move(s)."""
        move_ids = self._get_disposal_moves()
        if move_ids:
            name = _('Disposal Move')
            view_mode = 'form'
            if len(move_ids) > 1:
                name = _('Disposal Moves')
                view_mode = 'list,form'
            return {
                'name': name,
                'view_mode': view_mode,
                'res_model': 'account.move',
                'type': 'ir.actions.act_window',
                'target': 'current',
                'res_id': move_ids[0],
            }
        # Fallback, as if we just clicked on the smartbutton
        return self.open_entries()

    def set_to_draft(self):
        """Set the asset's state to 'draft'."""
        self.write({'state': 'draft'})

    @api.depends('value', 'salvage_value', 'depreciation_line_ids.move_check',
                 'depreciation_line_ids.amount')
    def _amount_residual(self):
        """Compute the residual value of the asset based on the total depreciation amount."""
        for record in self:
            total_amount = 0.0
            for line in record.depreciation_line_ids:
                if line.move_check:
                    total_amount += line.amount
            record.value_residual = record.value - total_amount - record.salvage_value

    @api.onchange('company_id')
    def onchange_company_id(self):
        """Update the 'currency_id' field based on the selected 'company_id'."""
        self.currency_id = self.company_id.currency_id.id

    @api.depends('depreciation_line_ids.move_id')
    def _entry_count(self):
        """Compute the number of entries related to the asset based on the depreciation lines."""
        for asset in self:
            res = self.env['account.asset.depreciation.line'].search_count(
                [('asset_id', '=', asset.id), ('move_id', '!=', False)])
            asset.entry_count = res or 0

    @api.constrains('prorata', 'method_time')
    def _check_prorata(self):
        """Check if prorata temporis can be applied for the given asset based on the 'prorata' and 'method_time' fields."""
        if self.prorata and self.method_time != 'number':
            raise ValidationError(_(
                'Prorata temporis can be applied only for time method "number of depreciations".'))

    @api.onchange('category_id')
    def onchange_category_id(self):
        """Update the fields of the asset based on the selected 'category_id'."""
        vals = self.onchange_category_id_values(self.category_id.id)
        # We cannot use 'write' on an object that doesn't exist yet
        if vals:
            for k, v in vals['value'].items():
                setattr(self, k, v)

    def onchange_category_id_values(self, category_id):
        """Update the fields of the asset based on the selected 'category_id'."""
        if category_id:
            category = self.env['account.asset.category'].browse(category_id)
            return {
                'value': {
                    'method': category.method,
                    'method_number': category.method_number,
                    'method_time': category.method_time,
                    'method_period': category.method_period,
                    'method_progress_factor': category.method_progress_factor,
                    'method_end': category.method_end,
                    'prorata': category.prorata,
                    'journal_id':category.journal_id.id,
                    'account_asset_id':category.account_asset_id.id,
                    'account_depreciation_id':category.account_depreciation_id.id,
                    'account_depreciation_expense_id':category.account_depreciation_expense_id.id,
                    'account_analytic_id':category.account_analytic_id.id
                }
            }

    @api.onchange('method_time')
    def onchange_method_time(self):
        """Update the 'prorata' field based on the selected 'method_time' value."""
        if self.method_time != 'number':
            self.prorata = False

    def copy_data(self, default=None):
        """Copies the data of the current record with the option to override default values."""
        if default is None:
            default = {}
        default['name'] = self.name + _(' (copy)')
        return super(AccountAssetAsset, self).copy_data(default)

    def _compute_entries(self, date, group_entries=False):
        """Compute depreciation entries for the given date."""
        depreciation_ids = self.env['account.asset.depreciation.line'].search([
            ('asset_id', 'in', self.ids), ('depreciation_date', '<=', date),
            ('move_check', '=', False)])
        if group_entries:
            return depreciation_ids.create_grouped_move()
        return depreciation_ids.create_move()

    def open_entries(self):
        """Return a dictionary to open journal entries related to the asset."""
        move_ids = []
        for asset in self:
            for depreciation_line in asset.depreciation_line_ids:
                if depreciation_line.move_id:
                    move_ids.append(depreciation_line.move_id.id)
        return {
            'name': _('Journal Entries'),
            'view_mode': 'list,form',
            'res_model': 'account.move',
            'views': [(self.env.ref('account.view_move_tree').id, 'list'), (False, 'form')],
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', move_ids)],
        }

    def action_save_model(self):
        return{
            'type': 'ir.actions.act_window',
            'name': _('Asset Model'),
            'res_model': 'account.asset.category',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_price': self.value,
                        'default_method_time':self.method_time,
                        'default_method_end':self.method_end,
                        'default_method_number':self.method_number,
                        'default_method_period':self.method_period,
                        'default_method':self.method,
                        'default_company_id':self.company_id.id,
                        'default_method_progress_factor':self.method_progress_factor,
                        'default_prorata':self.prorata,
                        'default_group_entries':self.group_entries,
                        'default_open_asset':self.open_asset,
                        'default_account_analytic_id':self.account_analytic_id.id,
                        'default_account_depreciation_expense_id':self.account_depreciation_expense_id.id,
                        'default_account_depreciation_id':self.account_depreciation_id.id,
                        'default_account_asset_id':self.account_asset_id.id,
                        'default_journal_id':self.journal_id.id,
                        'default_asset_id': self.id,
                        }
        }

    def action_cancel_assets(self):
        for asset in self:
            for move in asset.depreciation_line_ids.mapped('move_id'):
                if move.state == 'posted':
                    # Force to draft
                    move.button_draft()  # or move.state = 'draft' if button_draft is restricted
                move.unlink()

            # Delete all depreciation lines
            asset.depreciation_line_ids.unlink()

            # Reset state
            asset.state = 'cancelled'
