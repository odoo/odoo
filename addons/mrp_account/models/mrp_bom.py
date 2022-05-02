# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', company_dependent=True,
        domain="[('company_id', 'in', [company_id, False])]",
        help="Analytic account in which cost and revenue entries will take place for financial management of the manufacturing order.")

    @api.constrains('analytic_account_id', 'company_id')
    def _check_analytic_account_id(self):
        for bom in self:
            if bom.company_id and bom.analytic_account_id.company_id and bom.company_id != bom.analytic_account_id.company_id:
                raise ValidationError(_('The selected account belongs to another company than the bom: %s', bom.display_name))
