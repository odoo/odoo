# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PaymentMethod(models.Model):
    _name = 'payment.method'
    _description = "Payment Method"
    _order = 'sequence, name'

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(string="Sequence", default=1)
    code = fields.Char(
        string="Code",
        help="The technical code of this payment method.",
        required=True,
    )
    parent_id = fields.Many2one(
        string="Parent", help="The parent payment method", comodel_name='payment.method'
    )  # TODO ANV rename field
    child_payment_method_ids = fields.One2many(
        string="Child Payment Methods",
        help="TODO",
        comodel_name='payment.method',
        inverse_name='parent_id',
    )
    provider_ids = fields.Many2many(
        string="Providers",
        help="The list of providers supporting this payment method.",
        comodel_name='payment.provider',
    )
    image = fields.Image(
        string="Image",
        help="The base image used for this payment method; in a 64x64 px format.",
        max_width=64,
        max_height=64,
        required="True",
    )
    image_payment_form = fields.Image(
        string="The resized image displayed on the payment form.",
        related='image',
        store=True,
        max_width=45,
        max_height=30,
    )  # TODO see if still necessary; if ratio is still correct

    # === BUSINESS METHODS ===#

    def _get_compatible_payment_methods(self, provider_ids):
        """ TODO.

        """
        return self.search([('provider_ids', 'in', provider_ids), ('parent_id', '=', False)])

    def _get_from_code(self, code, mapping=None):
        """ Get the payment method corresponding to the given provider-specific code.

        If a mapping is given, the search uses the generic payment method code that corresponds to
        the given provider-specific code.

        :param str code: The provider-specific code of the payment method to get.
        :param dict mapping: A non-exhaustive mapping of generic payment method codes to
                             provider-specific codes.
        :return: The corresponding payment method, if any.
        :type: payment.method
        """
        generic_to_specific_mapping = mapping or {}
        specific_to_generic_mapping = {v: k for k, v in generic_to_specific_mapping.items()}
        return self.search([('code', '=', specific_to_generic_mapping.get(code, code))], limit=1)
