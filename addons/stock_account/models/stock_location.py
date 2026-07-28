# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class StockLocation(models.Model):
    _inherit = "stock.location"

    valuation_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account',
        domain=[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card'))],
        help="Expense account used to re-qualify products removed from stock and sent to this location")
    is_valued_internal = fields.Boolean('Is valued inside the company', compute="_compute_is_valued", search="_search_is_valued")
    is_valued_external = fields.Boolean('Is valued outside the company', compute="_compute_is_valued")

    @api.constrains('usage')
    def _check_usage_no_valued_moves(self):
        non_valued = self.filtered(lambda l: l.usage not in ('internal', 'transit'))
        if not non_valued:
            return
        move_lines = self.env['stock.move.line'].search([
            ('move_id.state', '=', 'done'),
            ('move_id.value', '!=', 0),
            '|',
            ('location_id', 'in', non_valued.ids),
            ('location_dest_id', 'in', non_valued.ids),
        ])
        if move_lines:
            non_valued_ids = set(non_valued.ids)
            offending_ids = (
                set(move_lines.mapped('location_id.id'))
                | set(move_lines.mapped('location_dest_id.id'))
            ) & non_valued_ids
            offending = self.browse(offending_ids)
            raise UserError(self.env._(
                "You cannot change the type of the following locations because they have stock moves with valuation:\n%(locations)s",
                locations='\n'.join(offending.mapped('display_name')),
            ))

    def _search_is_valued(self, operator, value):
        if operator not in ['=', '!=']:
            raise NotImplementedError(self.env._("Invalid search operator or value"))
        positive_operator = (operator == '=' and value) or (operator == '!=' and not value)
        domain = Domain([('company_id', 'in', self.env.companies.ids), ('usage', 'in', ['internal', 'transit'])])
        if positive_operator:
            return domain
        return ~domain

    def _compute_is_valued(self):
        for location in self:
            if location._should_be_valued():
                location.is_valued_internal = True
                location.is_valued_external = False
            else:
                location.is_valued_internal = False
                location.is_valued_external = True

    def _should_be_valued(self):
        """ This method returns a boolean reflecting whether the products stored in `self` should
        be considered when valuating the stock of a company.
        """
        self.ensure_one()
        return bool(self.company_id) and self.usage in ['internal', 'transit']
