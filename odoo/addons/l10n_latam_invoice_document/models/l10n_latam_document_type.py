# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api
from odoo.osv import expression


class L10nLatamDocumentType(models.Model):

    _name = 'l10n_latam.document.type'
    _description = 'Latam Document Type'
    _order = 'sequence, id'
    _rec_names_search = ['name', 'code']

    active = fields.Boolean(default=True)
    sequence = fields.Integer(
        default=10, required=True, help='To set in which order show the documents type taking into account the most'
        ' commonly used first')
    country_id = fields.Many2one(
        'res.country', required=True, index=True, help='Country in which this type of document is valid')
    name = fields.Char(required=True, help='The document name', translate=True)
    doc_code_prefix = fields.Char(
        'Document Code Prefix', help="Prefix for Documents Codes on Invoices and Account Moves. For eg. 'FA ' will"
        " build 'FA 0001-0000001' Document Number")
    code = fields.Char(help='Code used by different localizations')
    report_name = fields.Char('Name on Reports', help='Name that will be printed in reports, for example "CREDIT NOTE"', translate=True)
    internal_type = fields.Selection(
        [('invoice', 'Invoices'), ('debit_note', 'Debit Notes'), ('credit_note', 'Credit Notes'), ('all', 'All Documents')],
        help='Analog to odoo account.move.move_type but with more options allowing to identify the kind of document we are'
        ' working with. (not only related to account.move, could be for documents of other models like stock.picking)')

    def _format_document_number(self, document_number):
        """ Method to be inherited by different localizations. The purpose of this method is to allow:
        * making validations on the document_number. If it is wrong it should raise an exception
        * format the document_number against a pattern and return it
        """
        self.ensure_one()
        return document_number

    @api.depends('code')
    def _compute_display_name(self):
        for rec in self:
            name = rec.name
            if rec.code:
                name = f'({rec.code}) {name}'
            rec.display_name = name
