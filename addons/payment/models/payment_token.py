# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

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
        """ Prevent unarchiving tokens and handle their archiving.

        :return: The result of the call to the parent method.
        :rtype: bool
        :raise UserError: If at least one token is being unarchived.
        """
        if 'active' in values:
            if values['active']:
                if any(not token.active for token in self):
                    raise UserError(_("A token cannot be unarchived once it has been archived."))
            else:
                # Call the handlers in sudo mode because this method might have been called by RPC.
                self.filtered('active').sudo()._handle_archiving()

        return super().write(values)

    #=== BUSINESS METHODS ===#

    def _handle_archiving(self):
        """ Handle the archiving of the current tokens.

        For a module to perform additional operations when a token is archived, it must override
        this method.

        :return: None
        """
        return None

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
