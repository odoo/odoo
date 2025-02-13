# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    # ------------------
    # Fields declaration
    # ------------------

    is_withholding_tax_on_payment = fields.Boolean(
        string="Withholding On Payment",
        help="If enabled, this tax will not affect journal entries until the registration of payment.",
    )
    withholding_sequence_id = fields.Many2one(
        string='Withholding Sequence',
        help='Label displayed on Journal Items and Payment Receipts.',
        comodel_name='ir.sequence',
        copy=False,
        check_company=True,
    )
    color = fields.Integer(compute='_compute_color')

    def _compute_color(self):
        for tax in self:
            tax.color = 1 if tax.is_withholding_tax_on_payment else 0

    @api.onchange('is_withholding_tax_on_payment')
    def _onchange_is_withholding_tax_on_payment(self):
        """ Ensure that we don't keep cash basis enabled if it was before checking the withholding tax option. """
        if self.is_withholding_tax_on_payment:
            self.tax_exigibility = 'on_invoice'

    def _batch_for_taxes_computation(self, special_mode=False):
        # EXTEND account to remove withholding taxes from the batches and thus skip all computations for them.
        filtered_self = self
        # By default, we don't want withholding taxes to affect anything, but in some cases (payment wizard, withholding tax lines, ...)
        # the computation is still required.
        if not self.env.context.get('include_withholding_taxes'):
            filtered_self = self.filtered(lambda t: not t.is_withholding_tax_on_payment)
        return super(AccountTax, filtered_self)._batch_for_taxes_computation(special_mode=special_mode)
