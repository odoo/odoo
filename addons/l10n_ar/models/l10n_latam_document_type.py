from odoo import models, api, fields, _
from odoo.exceptions import UserError


class L10nLatamDocumentType(models.Model):

    _inherit = 'l10n_latam.document.type'

    l10n_ar_letter = fields.Selection(
        selection='_get_l10n_ar_letters',
        string='Letters',
        help='Letters defined by the AFIP that can be used to identify the'
        ' documents presented to the government and that depends on the'
        ' operation type, the responsibility of both the issuer and the'
        ' receptor of the document')
    purchase_aliquots = fields.Selection(
        [('not_zero', 'Not Zero'), ('zero', 'Zero')], help='Raise an error if a vendor bill is miss encoded. "Not Zero"'
        ' means the VAT taxes are required for the invoices related to this document type, and those with "Zero" means'
        ' that only "VAT Not Applicable" tax is allowed.')

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
            ('I', 'I'),  # used for mapping of imports
        ]
    def _filter_taxes_included(self, taxes):
        """ In argentina we include taxes depending on document letter """
        self.ensure_one()
        if self.country_id.code == "AR" and self.l10n_ar_letter in ['B', 'C', 'X', 'R']:
            return taxes.filtered(lambda x: x.tax_group_id.l10n_ar_vat_afip_code)
        return super()._filter_taxes_included(taxes)

    def _format_document_number(self, document_number):
        """ Make validation of Import Dispatch Number
          * making validations on the document_number. If it is wrong it should raise an exception
          * format the document_number against a pattern and return it
        """
        self.ensure_one()
        if self.country_id.code != "AR":
            return super()._format_document_number(document_number)

        if not document_number:
            return False

        msg = "'%s' " + _("is not a valid value for") + " '%s'.<br/>%s"

        if not self.code:
            return document_number

        # Import Dispatch Number Validator
        if self.code in ['66', '67']:
            if len(document_number) != 16:
                raise UserError(msg % (document_number, self.name, _('The number of import Dispatch must be 16 characters')))
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
            document_number = '{:>05s}-{:>08s}'.format(pos, number)
        if failed:
            raise UserError(msg % (document_number, self.name, _(
                'The document number must be entered with a dash (-) and a maximum of 5 characters for the first part'
                'and 8 for the second. The following are examples of valid numbers:\n* 1-1\n* 0001-00000001'
                '\n* 00001-00000001')))

        return document_number
