from odoo import api, fields, models


class L10nAeTransactionType(models.Model):
    """ An invoice transaction type (BTAE-02).

    The document carries them as one flag string of 8 characters, a position per transaction type,
    since several can apply to the same invoice: 00000011 is a supply through e-commerce that is
    also an export. Each type's code is that string with only its own position set.
    https://docs.peppol.eu/poac/ae/pint-ae/bis/#_invoice_transaction_type_code
    """
    _name = 'l10n_ae.transaction.type'
    _description = "UAE Invoice Transaction Type"
    _order = 'code desc'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, help="The flag string with only this type's position set, e.g. 00000001 for Exports.")

    _code_uniq = models.Constraint('UNIQUE(code)', "A transaction type code must be unique.")
    _code_format = models.Constraint(
        r"CHECK(code ~ '^0*10*$' AND length(code) = 8)",
        "A transaction type code is 8 characters, all 0 but its own position set to 1.",
    )

    def _get_flags_code(self):
        """ The flag string of these transaction types together, False if there are none. """
        flags = 0
        for code in self.mapped('code'):
            flags |= int(code, 2)
        return flags and f'{flags:08b}'

    @api.model
    def _get_from_flags_code(self, flags_code):
        """ The transaction types set in a flag string such as 00000011. """
        flags = int(flags_code, 2)
        return self.search([]).filtered(lambda transaction_type: int(transaction_type.code, 2) & flags)
