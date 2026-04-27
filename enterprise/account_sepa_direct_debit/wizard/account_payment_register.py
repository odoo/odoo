from odoo import Command, _, models, fields, api
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    sdd_mandate_usable = fields.Boolean(string="Could a SDD mandate be used?",
        compute='_compute_usable_mandate')

    no_sdd_mandate_partner_ids = fields.Many2many(comodel_name='res.partner', compute='_compute_usable_mandate')

    @api.depends('payment_date', 'partner_id', 'company_id', 'line_ids.partner_id')
    def _compute_usable_mandate(self):
        """ returns the first mandate found that can be used for this payment,
        or none if there is no such mandate.
        """
        for wizard in self:
            partners_with_valid_mandates = wizard._get_partner_ids_with_valid_mandates()
            wizard.no_sdd_mandate_partner_ids = wizard.line_ids.partner_id - self.env['res.partner'].browse(partners_with_valid_mandates)
            wizard.sdd_mandate_usable = not wizard.no_sdd_mandate_partner_ids

    def _get_partner_ids_with_valid_mandates(self):
        """
        Helper to search all partners that have at least one valid mandates
        :return: set of partner_ids
        :rtype: set
        """
        self.ensure_one()
        moves_to_pay = self.line_ids.move_id
        valid_mandate_ids_per_partner_id = self.env['sdd.mandate']._read_group([
                ('state', '=', 'active'),
                ('start_date', '<=', self.payment_date),
                '|', ('end_date', '=', False), ('end_date', '>=', self.payment_date),
                ('partner_id', 'in', moves_to_pay.partner_id.commercial_partner_id.ids),
                *self.env['sdd.mandate']._check_company_domain(moves_to_pay.company_id),
            ],
            groupby=['partner_id'],
        )
        return {partner.id for (partner,) in valid_mandate_ids_per_partner_id}

    def action_create_payments(self):
        """ Exclude the payments using SEPA direct debit from being generated if there is no valid mandate for their customer """
        # EXTENDS account
        sdd_codes = set(self.env['account.payment.method']._get_sdd_payment_method_code())

        for wizard in self.filtered(lambda wiz: wiz.payment_method_code in sdd_codes):
            valid_partner_ids = wizard._get_partner_ids_with_valid_mandates()
            if set(wizard.line_ids.partner_id.ids) != valid_partner_ids:
                wizard.write({
                    'line_ids': [Command.set(wizard.line_ids.filtered(lambda line: line.partner_id.id in valid_partner_ids).ids)],
                    # Avoid re-computation of these fields that depend on line_ids or sub compute triggered by line_ids
                    'payment_method_line_id': wizard.payment_method_line_id.id,
                    'group_payment': wizard.group_payment,
                })
            if not wizard.line_ids:
                raise UserError(_(
                    "You can't pay any of the selected invoices using the SEPA Direct Debit method, as no valid mandate is available"
                ))

        return super().action_create_payments()
