# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class AccountCommonReport(models.TransientModel):
    _inherit = "account.common.report"

    l10n_in_unit_id = fields.Many2one('res.partner', string='Unit')

    @api.onchange('company_id')
    def _onchange_company_id(self):
        res = super(AccountCommonReport, self)._onchange_company_id()
        if self.company_id and self.env.user.has_group('l10n_in.group_multi_operating_unit'):
            self.l10n_in_unit_id = self.env.user.l10n_in_unit_id or self.company_id.partner_id
        else:
            self.l10n_in_unit_id = False
        return res

    def _build_contexts(self, data):
        result = super(AccountCommonReport, self)._build_contexts(data)
        result['l10n_in_unit_id'] = data['form']['l10n_in_unit_id'] and data['form']['l10n_in_unit_id'][0] or False
        result['l10n_in_unit_name'] = data['form']['l10n_in_unit_id'] and data['form']['l10n_in_unit_id'][1] or False
        return result

    def check_report(self, fields=[]):
        self.ensure_one()
        fields.append('l10n_in_unit_id')
        return super(AccountCommonReport, self).check_report(fields)
