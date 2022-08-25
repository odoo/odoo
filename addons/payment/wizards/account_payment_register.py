from odoo import api, Command, fields, models


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
        help="Note that tokens from acquirers set to only authorize transactions (instead of capturing the amount) are "
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
    payment_method_code = fields.Char(
        related='payment_method_line_id.code')

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('payment_method_line_id')
    def _compute_suitable_payment_token_ids(self):
        for wizard in self:
            if wizard.can_edit_wizard and wizard.use_electronic_payment_method:
                related_partner_ids = (
                        wizard.partner_id
                        | wizard.partner_id.commercial_partner_id
                        | wizard.partner_id.commercial_partner_id.child_ids
                )._origin

                wizard.suitable_payment_token_ids = self.env['payment.token'].sudo().search([
                    ('company_id', '=', wizard.company_id.id),
                    ('acquirer_id.capture_manually', '=', False),
                    ('partner_id', 'in', related_partner_ids.ids),
                    ('acquirer_id', '=', wizard.payment_method_line_id.payment_acquirer_id.id),
                ])
            else:
                wizard.suitable_payment_token_ids = [Command.clear()]

    @api.depends('payment_method_line_id')
    def _compute_use_electronic_payment_method(self):
        for wizard in self:
            # Get a list of all electronic payment method codes.
            # These codes are comprised of the providers of each payment acquirer.
            codes = [key for key in dict(self.env['payment.acquirer']._fields['provider']._description_selection(self.env))]
            wizard.use_electronic_payment_method = wizard.payment_method_code in codes

    @api.onchange('can_edit_wizard', 'payment_method_line_id', 'journal_id')
    def _compute_payment_token_id(self):
        codes = [key for key in dict(self.env['payment.acquirer']._fields['provider']._description_selection(self.env))]
        for wizard in self:
            related_partner_ids = (
                    wizard.partner_id
                    | wizard.partner_id.commercial_partner_id
                    | wizard.partner_id.commercial_partner_id.child_ids
            )._origin
            if wizard.can_edit_wizard \
                    and wizard.payment_method_line_id.code in codes \
                    and wizard.journal_id \
                    and related_partner_ids:

                wizard.payment_token_id = self.env['payment.token'].sudo().search([
                    ('company_id', '=', wizard.company_id.id),
                    ('partner_id', 'in', related_partner_ids.ids),
                    ('acquirer_id.capture_manually', '=', False),
                    ('acquirer_id', '=', wizard.payment_method_line_id.payment_acquirer_id.id),
                 ], limit=1)
            else:
                wizard.payment_token_id = False

    # -------------------------------------------------------------------------
    # BUSINESS METHODS
    # -------------------------------------------------------------------------

    def _create_payment_vals_from_wizard(self):
        # OVERRIDE
        payment_vals = super()._create_payment_vals_from_wizard()
        payment_vals['payment_token_id'] = self.payment_token_id.id
        return payment_vals
