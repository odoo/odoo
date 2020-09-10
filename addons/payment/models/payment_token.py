# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class PaymentToken(models.Model):

    _name = 'payment.token'
    _order = 'partner_id, id desc'
    _description = 'Payment Token'

    name = fields.Char(
        string="Name", help="The anonymized acquirer reference of the payment method",
        required=True)
    partner_id = fields.Many2one(string="Partner", comodel_name='res.partner', required=True)
    acquirer_id = fields.Many2one(
        string="Acquirer Account", comodel_name='payment.acquirer', required=True)
    company_id = fields.Many2one(  # Indexed for ir.rule
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
                values.update(self._get_create_values(values, acquirer.provider))
            else:
                pass  # Let psycopg warn about the missing required field

        return super().create(values_list)

    @api.model
    def _get_create_values(self, _values, _provider):
        """ Complete the values of the `create` method with acquirer-specific values.

        For an acquirer to add its own create values, it must overwrite this method and return a
        dict of values. Acquirer-specific values take precedence over those of the dict of generic
        create values.

        :param dict _values: The original create values
        :param str _provider: The provider of the acquirer managing the token
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
                if values['active']:
                    token._handle_activation_request()
                else:
                    token._handle_deactivation_request()

        # Proceed with the toggling of the active state
        return super().write(values)

    #=== BUSINESS METHODS ===#

    def _handle_deactivation_request(self):
        """ Request the provider of the acquirer managing the token to disable it.

        For an acquirer to support deactivation of tokens, it must overwrite this method and send
        relevant requests to its provider or raise an UserError.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if an overriding acquirer forbids this operation
        """
        return

    def _handle_activation_request(self):
        """ Request the provider of the acquirer managing the token to restore it.

        For an acquirer to support activation of tokens, it must overwrite this method and send
        relevant requests to its provider or raise an UserError.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if an overriding acquirer forbids this operation
        """
        return

    def get_linked_records_info(self):
        """ Return a list of information about records linked to the current token.

        For a module to implement payments, it must override this method and complete the dict
        returned by this method with information about linked records.

        The information must be structured as a dict with the following keys:
          - description: The description of the record's model (e.g. "Subscription")
          - id: The id of the record
          - name: The name of the record
          - url: The url to access the record.

        Note: self.ensure_one()

        :return: The list of information about linked documents
        :rtype: dict
        """
        self.ensure_one()
        return []
