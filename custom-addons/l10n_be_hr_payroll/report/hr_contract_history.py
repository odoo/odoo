# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from collections import defaultdict


class ContractHistory(models.Model):
    _inherit = 'hr.contract.history'

    fiscal_voluntarism = fields.Boolean(
        string='Fiscal Voluntarism', readonly=True,
        help='Voluntarily increase withholding tax rate.')
    fiscal_voluntary_rate = fields.Float(string='Fiscal Voluntary Rate', readonly=True,
        help='Should be between 0 and 100 %')
    l10n_be_is_below_scale = fields.Boolean(
        string="Is below CP200 salary scale", compute='_compute_l10n_be_is_below_scale', search='_search_l10n_be_is_below_scale')
    l10n_be_is_below_scale_warning = fields.Char(compute='_compute_l10n_be_is_below_scale')
    has_valid_schedule_change_contract = fields.Boolean(
        compute='_compute_has_valid_schedule_change_contract',
        help="Whether or not the employee has a contract candidate for a working schedule change")

    @api.depends('contract_id')
    def _compute_l10n_be_is_below_scale(self):
        for history in self:
            history.l10n_be_is_below_scale = history.contract_id.l10n_be_is_below_scale
            history.l10n_be_is_below_scale_warning = history.contract_id.l10n_be_is_below_scale_warning

    @api.model
    def _search_l10n_be_is_below_scale(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise NotImplementedError(_('Operation not supported'))
        below_histories = self.env['hr.contract.history'].search(
            [('state', 'in', ['draft', 'open'])]
        ).filtered(lambda h: h.company_id.country_id.code == 'BE' and h.contract_id.l10n_be_is_below_scale)

        if operator == '!=':
            value = not value
        return [('id', 'in' if value else 'not in', below_histories.ids)]

    @api.depends('contract_ids')
    def _compute_has_valid_schedule_change_contract(self):
        for history in self:
            history.has_valid_schedule_change_contract = bool(self.contract_ids.filtered(lambda c: c.state in ('draft', 'open')))

    def action_work_schedule_change_wizard(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('l10n_be_hr_payroll.schedule_change_wizard_action')
        #Use the valid contract starting on the furthest date
        valid_contracts = self.contract_ids.filtered(lambda c: c.state in ('draft', 'open'))
        if not valid_contracts:
            return False
        contract_id = valid_contracts.sorted('date_start')[-1]
        action['context'] = {'active_id': contract_id.id}
        return action
