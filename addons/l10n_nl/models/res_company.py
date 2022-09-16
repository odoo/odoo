# coding: utf-8
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_nl_kvk = fields.Char(related='partner_id.l10n_nl_kvk', readonly=False)
    l10n_nl_oin = fields.Char(related='partner_id.l10n_nl_oin', readonly=False)

    early_pay_discount_computation = fields.Selection([
        ('included', 'On early payment'),
        ('excluded', 'Never'),
        ('mixed', 'Always (upon invoice)')
    ], string='Cash Discount Tax Reduction', default='excluded', readonly=False)
