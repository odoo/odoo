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
    code = fields.Selection(
        selection=[
            ('10000000', 'Free Trade Zone'),
            ('01000000', 'Deemed Supply'),
            ('00100000', 'Profit Margin Scheme'),
            ('00010000', 'Summary'),
            ('00001000', 'Continuous Supply'),
            ('00000100', 'Disclosed Agent Billing'),
            ('00000010', 'Supply through e-commerce'),
            ('00000001', 'Exports'),
        ],
        required=True,
        help="The flag string with only this type's position set, e.g. 00000001 for Exports.",
    )

    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)', "A transaction type code must be unique."),
    ]

    def _get_flags_code(self):
        """ The flag string of these transaction types together, False if there are none. """
        flags = 0
        for code in self.mapped('code'):
            flags |= int(code, 2)
        return flags and f'{flags:08b}'

    @api.model
    def _get_from_flags_code(self, flags_code):
        """ The transaction types set in a flag string such as 00000011. """
        codes = [
            '0' * position + '1' + '0' * (len(flags_code) - position - 1)
            for position, flag in enumerate(flags_code)
            if flag == '1'
        ]
        return self.search([('code', 'in', codes)])
