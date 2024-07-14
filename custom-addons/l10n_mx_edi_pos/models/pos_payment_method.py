# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    l10n_mx_edi_payment_method_id = fields.Many2one(
        comodel_name='l10n_mx_edi.payment.method',
        string="Payment Way",
        compute='_compute_l10n_mx_edi_payment_method_id',
        store=True,
        readonly=False,
        help="Indicates the way the invoice was/will be paid, where the options could be: "
             "Cash, Nominal Check, Credit Card, etc. Leave empty if unknown and the XML will show 'Unidentified'.",
    )

    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id.country_id'])

    @api.depends('journal_id')
    def _compute_l10n_mx_edi_payment_method_id(self):
        por_definir_payment_method = self.env.ref('l10n_mx_edi.payment_method_otros', raise_if_not_found=False)
        for move in self:
            if move.l10n_mx_edi_payment_method_id:
                move.l10n_mx_edi_payment_method_id = move.l10n_mx_edi_payment_method_id
            elif move.journal_id.l10n_mx_edi_payment_method_id:
                move.l10n_mx_edi_payment_method_id = move.journal_id.l10n_mx_edi_payment_method_id
            else:
                move.l10n_mx_edi_payment_method_id = por_definir_payment_method
