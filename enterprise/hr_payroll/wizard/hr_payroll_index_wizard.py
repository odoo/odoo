# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_date


class HrPayrollIndex(models.TransientModel):
    _name = 'hr.payroll.index'
    _description = 'Index contracts'

    def _get_default_contract_ids(self):
        if self.env.context.get("active_ids"):
            return self.env.context.get("active_ids")
        return self.env['hr.contract'].search([('state', '=', 'open')])

    percentage = fields.Float("Percentage")
    description = fields.Char(
        "Description", compute='_compute_description', store=True, readonly=False,
        help="Will be used as the message specifying why the wage on the contract has been modified")
    contract_ids = fields.Many2many(
        'hr.contract', string="Contracts",
        default=_get_default_contract_ids,
    )
    display_warning = fields.Boolean("Error", compute='_compute_display_warning')

    @api.depends('contract_ids')
    def _compute_display_warning(self):
        for index in self:
            contracts = index.contract_ids
            index.display_warning = any(contract.state != 'open' for contract in contracts)

    @api.depends('percentage')
    def _compute_description(self):
        for record in self:
            record.description = _(
                'Wage indexed by %(percentage).2f%% on %(date)s',
                percentage=self.percentage * 100,
                date=format_date(self.env, fields.Date.today()),
            )

    @api.model
    def _index_wage(self, contract):
        wage_field = contract._get_contract_wage_field()
        wage = contract[wage_field]
        contract.write({wage_field: wage * (1 + self.percentage)})

    def action_confirm(self):
        self.ensure_one()

        if self.display_warning:
            raise UserError(_('You have selected non running contracts, if you really need to index them, please do it by hand'))

        if self.percentage:
            for contract in self.contract_ids:
                self._index_wage(contract)
                contract.with_context(mail_create_nosubscribe=True).message_post(body=self.description, message_type="comment", subtype_xmlid="mail.mt_note")
