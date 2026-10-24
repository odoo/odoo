# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.fields import Domain


class StockLocation(models.Model):
    _inherit = "stock.location"

    valuation_account_id = fields.Many2one(
        'account.account', 'Stock Valuation Account',
        domain=[('account_type', 'not in', ('asset_receivable', 'liability_payable', 'asset_cash', 'liability_credit_card'))],
        help="Expense account used to re-qualify products removed from stock and sent to this location")
    is_valued_internal = fields.Boolean('Is valued inside the company', compute="_compute_is_valued", search="_search_is_valued")
    is_valued_external = fields.Boolean('Is valued outside the company', compute="_compute_is_valued")

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

    def _revalue_moves_through_location(self):
        """ Recompute `is_in`/`is_out` for every already-`done` move that passed through `self`,
        and revalue (`_set_value`) whichever ones actually flip. `is_in`/`is_out` are stored,
        computed fields whose @api.depends only lists ('state', 'move_line_ids') — a location's
        own `company_id`/`usage` is not tracked as a dependency, so moves already `done` through
        a location never get their valued-status reassessed if that location's configuration
        changes afterwards (e.g. a shared transit location's company_id being cleared/set after
        moves already passed through it). This can silently desynchronize the AVCO/FIFO replay
        (which trusts the frozen is_in/is_out/value) from the location-based "qty at a past
        date" reconstruction (which re-evaluates `_should_be_valued()` live on every read).
        """
        moves = self.env['stock.move'].search([
            ('state', '=', 'done'),
            '|', ('location_id', 'in', self.ids), ('location_dest_id', 'in', self.ids),
        ])
        if not moves:
            return self.env['stock.move']
        changed_moves = self.env['stock.move']
        for move in moves:
            # `_is_in()`/`_is_out()` can return an empty recordset instead of a bare `False`
            # when falsy (they're `a and not b` expressions) - cast explicitly so comparing
            # against the already-coerced, stored boolean field doesn't always look "changed".
            new_is_in, new_is_out = bool(move._is_in()), bool(move._is_out())
            if new_is_in != move.is_in or new_is_out != move.is_out:
                move.is_in, move.is_out = new_is_in, new_is_out
                changed_moves |= move
        if changed_moves:
            changed_moves._set_value()
        return changed_moves

    def action_revalue_moves_through_location(self):
        """ Manual entry point (e.g. a form button) to recompute valuation for every move
        through this location, for cases where the location's valued status changed without
        going through `write()` (e.g. a direct data fix, import, or migration).
        """
        self.ensure_one()
        changed_moves = self._revalue_moves_through_location()
        if changed_moves:
            message = self.env._(
                "Recomputed valuation for %(count)s move(s) through this location.",
                count=len(changed_moves),
            )
        else:
            message = self.env._("No move through this location needed revaluation.")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': self.env._("Valuation recomputed"),
                'message': message,
                'type': 'success' if changed_moves else 'info',
                'sticky': False,
            },
        }
