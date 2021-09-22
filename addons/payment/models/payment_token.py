# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class PaymentToken(models.Model):
    _name = 'payment.token'
    _order = 'partner_id, id desc'
    _description = 'Payment Token'

    acquirer_id = fields.Many2one(
        string="Acquirer Account", comodel_name='payment.acquirer', required=True)
    provider = fields.Selection(related='acquirer_id.provider')
    name = fields.Char(
        string="Name", help="The anonymized acquirer reference of the payment method",
        required=True)
    partner_id = fields.Many2one(string="Partner", comodel_name='res.partner', required=True)
    company_id = fields.Many2one(  # Indexed to speed-up ORM searches (from ir_rule or others)
        related='acquirer_id.company_id', store=True, index=True)
    acquirer_ref = fields.Char(
        string="Acquirer Reference", help="The acquirer reference of the token of the transaction",
        required=True)  # This is not the same thing as the acquirer reference of the transaction
    transaction_ids = fields.One2many(
        string="Payment Transactions", comodel_name='payment.transaction', inverse_name='token_id')
    verified = fields.Boolean(string="Verified")
    active = fields.Boolean(string="Active", default=True)

    #=== CRUD METHODS ===#

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            if 'acquirer_id' in values:
                acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])

                # Include acquirer-specific create values
                values.update(self._get_specific_create_values(acquirer.provider, values))
            else:
                pass  # Let psycopg warn about the missing required field

        return super().create(values_list)

    @api.model
    def _get_specific_create_values(self, provider, values):
        """ Complete the values of the `create` method with acquirer-specific values.

        For an acquirer to add its own create values, it must overwrite this method and return a
        dict of values. Acquirer-specific values take precedence over those of the dict of generic
        create values.

        :param str provider: The provider of the acquirer managing the token
        :param dict values: The original create values
        :return: The dict of acquirer-specific create values
        :rtype: dict
        """
        return dict()

    def write(self, values):
        """ Delegate the handling of active state switch to dedicated methods.

        Unless an exception is raised in the handling methods, the toggling proceeds no matter what.
        This is because allowing users to hide their saved payment methods comes before making sure
        that the recorded payment details effectively get deleted.

        :return: The result of the write
        :rtype: bool
        """
        # Let acquirers handle activation/deactivation requests
        if 'active' in values:
            for token in self:
                # Call handlers in sudo mode because this method might have been called by RPC
                if values['active'] and not token.active:
                    token.sudo()._handle_reactivation_request()
                elif not values['active'] and token.active:
                    token.sudo()._handle_deactivation_request()

        # Proceed with the toggling of the active state
        return super().write(values)

    #=== BUSINESS METHODS ===#

    def _handle_deactivation_request(self):
        """ Handle the request for deactivation of the token.

        For an acquirer to support deactivation of tokens, or perform additional operations when a
        token is deactivated, it must overwrite this method and raise an UserError if the token
        cannot be deactivated.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()

    def _handle_reactivation_request(self):
        """ Handle the request for reactivation of the token.

        For an acquirer to support reactivation of tokens, or perform additional operations when a
        token is reactivated, it must overwrite this method and raise an UserError if the token
        cannot be reactivated.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()

    def get_linked_records_info(self):
        """ Return a list of information about records linked to the current token.

        For a module to implement payments and link documents to a token, it must override this
        method and add information about linked records to the returned list.

        The information must be structured as a dict with the following keys:
          - description: The description of the record's model (e.g. "Subscription")
          - id: The id of the record
          - name: The name of the record
          - url: The url to access the record.

        Note: self.ensure_one()

        :return: The list of information about linked documents
        :rtype: list
        """
        self.ensure_one()
        return []
