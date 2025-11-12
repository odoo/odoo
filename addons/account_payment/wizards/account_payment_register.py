from odoo import api, fields, models
from odoo.fields import Command, Domain


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    # == Business fields ==
    payment_token_id = fields.Many2one(
        comodel_name='payment.token',
        string="Saved payment token",
        store=True, readonly=False,
        compute='_compute_payment_token_id',
        domain='''[
            ('id', 'in', suitable_payment_token_ids),
        ]''',
        help="Note that tokens from providers set to only authorize transactions (instead of capturing the amount) are "
             "not available.")

    # == Display purpose fields ==
    suitable_payment_token_ids = fields.Many2many(
        comodel_name='payment.token',
        compute='_compute_suitable_payment_token_ids'
    )
    # Technical field used to hide or show the payment_token_id if needed
    use_electronic_payment_method = fields.Boolean(
        compute='_compute_use_electronic_payment_method',
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('payment_method_line_id')
    def _compute_suitable_payment_token_ids(self):
        for wizard in self:
            if (
                wizard.can_edit_wizard
                and wizard.use_electronic_payment_method
                and (provider := wizard.payment_method_line_id.payment_provider_id)
                and not provider.capture_manually
            ):
                token_partners = wizard.partner_id
                batch = wizard._get_batches()[0]
                lines_partners = batch['lines'].move_id.partner_id
                if len(lines_partners) == 1:
                    token_partners |= lines_partners
                wizard.suitable_payment_token_ids = self.env['payment.token'].sudo().search(
                    Domain.AND([
                        Domain('partner_id', 'in', token_partners.ids),
                        Domain('provider_id', '=', provider.id),
                        self.env['payment.token']._check_company_domain(wizard.company_id),
                    ]),
                )
            else:
                wizard.suitable_payment_token_ids = [Command.clear()]

    @api.depends('payment_method_line_id')
    def _compute_use_electronic_payment_method(self):
        # Get all electronic payment method codes.
        # These codes are comprised of the codes of each payment provider.
        codes = dict(self.env['payment.provider']._fields['code']._description_selection(self.env))
        for wizard in self:
            wizard.use_electronic_payment_method = wizard.payment_method_code in codes

    @api.depends('can_edit_wizard', 'suitable_payment_token_ids', 'journal_id')
    def _compute_payment_token_id(self):
        codes = dict(self.env['payment.provider']._fields['code']._description_selection(self.env))
        for wizard in self:
            if wizard.payment_method_line_id and wizard.payment_method_line_id.code not in codes:
                wizard.payment_token_id = False
            elif wizard.payment_token_id in wizard.suitable_payment_token_ids:
                # The selected payment token is still valid.
                continue
            else:
                wizard.payment_token_id = wizard.suitable_payment_token_ids[:1]

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _create_payment_vals_from_wizard(self, batch_result):
        # OVERRIDE
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals['payment_token_id'] = self.payment_token_id.id
        return payment_vals
