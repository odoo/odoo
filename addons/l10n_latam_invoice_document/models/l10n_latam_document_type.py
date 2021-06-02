# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class L10nLatamDocumentType(models.Model):

    _name = 'l10n_latam.document.type'
    _description = 'Latam Document Type'
    _order = 'sequence, id'

    active = fields.Boolean(default=True)
    sequence = fields.Integer(
        default=10, required=True, help='To set in which order show the documents type taking into account the most'
        ' commonly used first')
    country_id = fields.Many2one(
        'res.country', required=True, index=True, help='Country in which this type of document is valid')
    name = fields.Char(required=True, index=True, help='The document name')
    doc_code_prefix = fields.Char(
        'Document Code Prefix', help="Prefix for Documents Codes on Invoices and Account Moves. For eg. 'FA ' will"
        " build 'FA 0001-0000001' Document Number")
    code = fields.Char(help='Code used by different localizations')
    report_name = fields.Char('Name on Reports', help='Name that will be printed in reports, for example "CREDIT NOTE"')
    internal_type = fields.Selection(
        [('invoice', 'Invoices'), ('debit_note', 'Debit Notes'), ('credit_note', 'Credit Notes')], index=True,
        help='Analog to odoo account.move.type but with more options allowing to identify the kind of document we are'
        ' working with. (not only related to account.move, could be for documents of other models like stock.picking)')

    def _format_document_number(self, document_number):
        """ Method to be inherited by different localizations. The purpose of this method is to allow:
        * making validations on the document_number. If it is wrong it should raise an exception
        * format the document_number against a pattern and return it
        """
        self.ensure_one()
        return document_number

    def name_get(self):
        result = []
        for rec in self:
            name = rec.name
            if rec.code:
                name = '(%s) %s' % (rec.code, name)
            result.append((rec.id, name))
        return result

    def _filter_taxes_included(self, taxes):
        """ This method is to be inherited by different localizations and must return filter the given taxes recordset
        returning the taxes to be included on reports of this document type. All taxes are going to be discriminated
        except the one returned by this method. """
        self.ensure_one()
        return self.env['account.tax']

    def _get_document_sequence_vals(self, journal):
        self.ensure_one()
        return {'name': '%s - %s' % (journal.name, self.name), 'padding': 8, 'prefix': self.code}
