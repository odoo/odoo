from odoo import fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    l10n_pk_edi_pos_enabled = fields.Boolean(
        string="Pakistan electronic receipts (FBR)",
        help="Submit your orders to the FBR to generate compliant receipts.",
    )
    l10n_pk_edi_pos_identifier = fields.Char(
        string="Shop ID",
        help="Shop ID provided by the FBR when registering your point of sale.",
    )
    l10n_pk_edi_pos_test_identifier = fields.Char(
        string="Test Shop ID",
        help="Shop ID provided by the FBR for the sandbox environment.",
    )
    l10n_pk_edi_pos_token = fields.Char(
        string="Shop Token",
        help="Shop Token provided by the FBR when registering your point of sale.",
    )
    l10n_pk_edi_pos_charge_service_fee = fields.Boolean(
        string="Charge Service Fee",
        help="Add the FBR service fee to the customer receipt.",
    )
    l10n_pk_edi_pos_service_fee_product_id = fields.Many2one(
        comodel_name='product.product',
        string="Service Fee Product",
        default=lambda self: self.env.ref(
            'l10n_pk_edi_pos.product_product_fbr_service_fee', raise_if_not_found=False
        ),
        help="Product used to charge the FBR service fee on the receipt.",
    )
    l10n_pk_edi_pos_sandbox = fields.Boolean(
        string="Use Sandbox Environment",
        help="Submit orders to the FBR sandbox environment for testing.",
    )

    def _l10n_pk_edi_pos_credentials(self):
        self.ensure_one()
        if not self.l10n_pk_edi_pos_sandbox:
            return self.l10n_pk_edi_pos_identifier, self.l10n_pk_edi_pos_token
        token = self.env['ir.config_parameter'].sudo().get_str('l10n_pk_edi_pos.sandbox_token')
        return self.l10n_pk_edi_pos_test_identifier, token

    def _get_special_products(self):
        # EXTENDS 'point_of_sale'
        products = super()._get_special_products()
        default_fee_product = self.env.ref('l10n_pk_edi_pos.product_product_fbr_service_fee', raise_if_not_found=False)
        if default_fee_product:
            products |= default_fee_product
        configs = self.env['pos.config'].search([])
        return products | configs.l10n_pk_edi_pos_service_fee_product_id
