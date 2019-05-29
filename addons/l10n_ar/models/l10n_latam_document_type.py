from odoo import models, api, fields, _
from odoo.exceptions import UserError

class L10nLatamDocumentType(models.Model):

    _inherit = 'l10n_latam.document.type'

    l10n_ar_letter = fields.Selection(
        selection='_get_l10n_ar_letters',
        string='Letters',
        help='Letters defined by the AFIP that can be used to identify the'
        ' documents presented to the goverment and that depends on the'
        ' operation type, the responsability of both the issuer and the'
        ' receptor or the document. The possible letters are:\n'
        '* A\n'
        '* B\n'
        '* C\n'
        '* E\n'
        '* M\n'
        '* T\n',
    )
    internal_type = fields.Selection(
        selection_add=[
            ('invoice', 'Invoices'),
            ('debit_note', 'Debit Notes'),
            ('credit_note', 'Credit Notes'),
        ],
    )
    purchase_cuit_required = fields.Boolean(
        help='Verdadero si la declaración del CITI compras requiere informar '
        'CUIT'
    )
    purchase_alicuots = fields.Selection(
        [('not_zero', 'No Cero'), ('zero', 'Cero')],
        help='Cero o No cero según lo requiere la declaración del CITI compras'
    )

    def _get_l10n_ar_letters(self):
        """ Return the list of values of the selection field. """
        return [
            ('A', 'A'),
            ('B', 'B'),
            ('C', 'C'),
            ('E', 'E'),
            ('M', 'M'),
            ('T', 'T'),
            ('R', 'R'),
            ('X', 'X'),
        ]

    @api.multi
    def get_document_sequence_vals(self, journal):
        """ Values to create the sequences
        """
        values = super(
            L10nLatamDocumentType, self).get_document_sequence_vals(journal)
        if self.country_id != self.env.ref('base.ar'):
            return values

        values.update({
            'padding': 8,
            'implementation': 'no_gap',
            'prefix': "%04i-" % (journal.l10n_ar_afip_pos_number),
            'l10n_latam_journal_id': journal.id,
        })
        if journal.l10n_ar_share_sequences:
            values.update({
                'name': '%s - Letter %s Documents' % (
                    journal.name, self.l10n_ar_letter),
                'l10n_ar_letter': self.l10n_ar_letter,
            })
        else:
            values.update({
                'name': '%s - %s' % (journal.name, self.name),
                'l10n_latam_document_type_id': self.id,
            })
        return values

    @api.multi
    def _get_taxes_included(self):
        """ In argentina we include taxes depending on document letter
        """
        self.ensure_one()
        if self.country_id == self.env.ref('base.ar') and self.l10n_ar_letter in [
           'B', 'C', 'X', 'R']:
            return self.env['account.tax'].search(
                [('tax_group_id.l10n_ar_tax', '=', 'vat'),
                 ('tax_group_id.l10n_ar_type', '=', 'tax')])
        return super()._get_taxes_included()

    @api.multi
    def _format_document_number(self, document_number):
        """ Method to be inherited by different localizations.
        The purpose of this method is to allow:

          * making validations on the document_number. If it is wrong it
            should raise an exception
          * format the document_number against a pattern and return it
        """
        self.ensure_one()
        if self.country_id != self.env.ref('base.ar'):
            return super()._format_document_number()

        if not document_number:
            return False

        msg = _("'%s' is not a valid value for '%s'.\n%s")

        # Import Dispatch Validator
        if self.code in ['66', '67']:
            if len(document_number) != 16:
                raise UserError(msg % (document_number, self.name, (
                    'El número de despacho de importación debe tener'
                    ' 16 caractéres')))
            return document_number

        # Invoice Number Validator (For Eg: 123-123)
        failed = False
        args = document_number.split('-')
        if len(args) != 2:
            failed = True
        else:
            pos, number = args
            if len(pos) > 5 or not pos.isdigit():
                failed = True
            elif len(number) > 8 or not number.isdigit():
                failed = True
            document_number = '{:>04s}-{:>08s}'.format(pos, number)
        if failed:
            raise UserError(msg % (document_number, self.name, (
                'El número de documento debe ingresarse con un guión (-) y'
                ' máximo 5 caracteres para la primer parte y 8 para la'
                ' segunda. Los siguientes son ejemplos de números válidos:'
                '\n* 1-1'
                '\n* 0001-00000001'
                '\n* 00001-00000001'
            )))
        return document_number
