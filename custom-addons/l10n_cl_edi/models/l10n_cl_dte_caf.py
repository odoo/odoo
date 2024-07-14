# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from lxml import etree

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class L10nClDteCaf(models.Model):
    _name = 'l10n_cl.dte.caf'
    _inherit = 'l10n_cl.edi.util'
    _description = 'CAF Files for chilean electronic invoicing'
    _rec_name = 'filename'
    """
    This models allows to manage the XML file delivered from the SII to the company, that allows to use it as a
    previous authorization to create electronic invoices.
    CAF: means 'Código de Autorización de Folios' (authorization from SII to generate a range of invoice numbers, from
    start_nb to final_nb. If the user consumes the authorized range of invoices, he must ask the SII for a further 
    authorization in order to continue with electronic invoices generation.
    If the company has pending issues with the SII (delay in paying taxes, or fail on formal requirements the SII 
    can deny to provide these files, until the company corrects the situation.
    """

    filename = fields.Char('File Name')
    caf_file = fields.Binary(string='CAF XML File',
                             help='Upload the CAF XML File in this holder')
    issued_date = fields.Date('Issued Date')
    l10n_latam_document_type_id = fields.Many2one('l10n_latam.document.type', string='Document Type')
    start_nb = fields.Integer(string='Start Number', help='CAF Starts from this number')
    final_nb = fields.Integer(string='End Number', help='CAF Ends to this number')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, readonly=True)
    status = fields.Selection([
        ('in_use', 'In Use'),
        ('spent', 'Spent')], string='Status',
        help='In Use: means that the CAF file is being used. Spent: means that the number interval '
             'has been exhausted.')

    _sql_constraints = [
        ('filename_unique', 'unique(filename)', 'Error! Filename Already Exist!')
    ]

    def _decode_caf(self):
        """
        This method decodes the file that comes in iso-8859-1 and transforms it to an etree object
        """
        post = base64.b64decode(self.caf_file).decode('ISO-8859-1')
        return etree.fromstring(post.encode('utf-8'))

    def action_enable(self):
        """
        This method gathers information from the caf file, analyze the tags and validate it, comparing the vat
        number of the company, with the vat present in the CAF.
        """
        try:
            result = self._decode_caf().xpath('//AUTORIZACION/CAF/DA')[0]
        except Exception:
            raise UserError(_('It\'s not a valid XML caf file'))
        self.start_nb = int(result.xpath('RNG/D')[0].text)
        self.final_nb = int(result.xpath('RNG/H')[0].text)
        l10n_latam_document_type_code = result.xpath('TD')[0].text
        self.l10n_latam_document_type_id = self.env['l10n_latam.document.type'].search([
            ('code', '=', l10n_latam_document_type_code),
            ('country_id.code', '=', 'CL'),
        ], limit=1)
        self.issued_date = result.xpath('FA')[0].text
        rut_n = result.xpath('RE')[0].text
        if not self.company_id.vat:
            raise UserError(_('The VAT of your company has not been configured. '
                              'Please go to your company data and add it.'))
        if self._l10n_cl_format_vat(rut_n) != self._l10n_cl_format_vat(self.company_id.vat):
            raise UserError(_('Caf vat %s should be the same that assigned company\'s vat: %s!') % (
                rut_n, self.company_id.vat))
        self.status = 'in_use'

    def action_spend(self):
        self.status = 'spent'

    @api.model_create_multi
    def create(self, vals_list):
        files = super().create(vals_list)
        for file in files:
            file.action_enable()
        return files
