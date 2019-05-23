# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class AccountJournal(models.Model):

    _inherit = "account.journal"

    _l10n_ar_afip_pos_types_selection = [
        ('II_IM', 'Factura Pre-impresa'),
        ('RLI_RLM', 'Factura en Linea'),
        ('CF', 'Controlador Fiscal'),
        ('BFERCEL', 'Bonos Fiscales Electrónicos - Factura en Linea'),
        ('FEERCELP', 'Comprobantes de Exportacion - Facturador Plus'),
        ('FEERCEL', 'Comprobantes de Exportacion - Factura en Linea'),
    ]

    l10n_ar_afip_pos_system = fields.Selection(
        _l10n_ar_afip_pos_types_selection,
        'AFIP POS System',
    )
    l10n_ar_afip_pos_number = fields.Integer(
        'AFIP POS Number',
        help='This is the point of sale number assigned by AFIP in order to'
        ' you in order to generate invoices',
    )
    l10n_ar_afip_pos_partner_id = fields.Many2one(
        'res.partner',
        'AFIP POS Address',
        help='This is the address used for invoice reports of this POS',
    )
    l10n_ar_sequence_ids = fields.One2many(
        'ir.sequence',
        'l10n_latam_journal_id',
    )
    l10n_ar_share_sequences = fields.Boolean(
        'Unified Book',
        help='Use same sequence for documents with the same letter',
    )

    def get_journal_letter(self, counterpart_partner=False):
        self.ensure_one()
        return self._get_journal_letter(
            journal_type=self.type,
            company=self.company_id,
            counterpart_partner=counterpart_partner)

    @api.model
    def _get_letters_data(self):
        """ Dictionary the the information about the letters, which
        responsability can used and the kind of operation received/issued
        """
        res = {
            'issued': {
                '1': ['A', 'B', 'E'],
                '1FM': ['B', 'M'],
                '3': [],
                '4': ['C'],
                '5': [],
                '6': ['C', 'E'],
                '8': [],
                '9': [],
                '10': [],
                '13': ['C', 'E'],
            },
            'received': {
                '1': ['A', 'C', 'M'],
                '1FM': ['A', 'M'],
                '3': ['B', 'C'],
                '4': ['B', 'C'],
                '5': ['B', 'C'],
                '6': ['B', 'C'],
                '8': ['E'],
                '9': ['E'],
                '10': ['E'],
                '13': ['B', 'C'],
            },
        }
        return res

    @api.model
    def _get_journal_letter(
            self, journal_type, company, counterpart_partner=False):
        """ Regarding the AFIP responsability of the company and the type of
        journal (sale/purchase), get the allowed letters.
        Optionally, receive the counterpart partner (customer/supplier) and
        get the allowed letters to work with him.
        This method is used to populate document types on journals and also
        to filter document types on specific invoices to/from customer/supplier
        """
        letters_data = self._get_letters_data()
        if not company.l10n_ar_afip_responsability_type:
            raise UserError(_(
                'Need to configure your company AFIP responsability first!'))
        letters = letters_data[
            'issued' if journal_type == 'sale' else 'received'][
            company.l10n_ar_afip_responsability_type]
        if counterpart_partner:
            if not counterpart_partner.l10n_ar_afip_responsability_type:
                letters = []
            else:
                counterpart_letters = letters_data[
                    'issued' if journal_type == 'purchase' else 'received'][
                        counterpart_partner.l10n_ar_afip_responsability_type]
                letters = list(set(letters) & set(counterpart_letters))
        return letters

    def get_journal_codes(self):
        self.ensure_one()
        usual_codes = [
            '1', '2', '3', '6', '7', '8', '11', '12', '13', '201', '202',
            '203', '206', '207', '208', '211', '212', '213']
        # facturam_codes = ['51', '52', '53']
        # recibo_m_code = '54'
        receipt_codes = ['4', '9', '15']
        expo_codes = ['19', '20', '21']
        if self.type != 'sale':
            return []
        elif self.l10n_ar_afip_pos_system in ['RAW_MAW', 'RLI_RLM', 'II_IM']:
            return usual_codes + receipt_codes
        elif self.l10n_ar_afip_pos_system in ['BFERCEL', 'BFEWS']:
            return usual_codes
        elif self.l10n_ar_afip_pos_system in ['FEERCEL', 'FEEWS', 'FEERCELP']:
            return expo_codes

    def get_document_type_sequence(self, invoice):
        """ Return the match sequences for the given journal and invoice
        """
        self.ensure_one()
        if self.l10n_latam_country_code != 'AR':
            return False
        if self.l10n_ar_share_sequences:
            return self.l10n_ar_sequence_ids.filtered(
                lambda x: x.l10n_ar_letter == invoice.l10n_ar_letter)

        return self.l10n_ar_sequence_ids.filtered(
            lambda x: x.l10n_latam_document_type_id ==
                invoice.l10n_latam_document_type_id)

    def create_document_type_sequences(self):
        """ Search if exist, it need to me updated? (can be?), or create
        """
        self.ensure_one()
        if self.company_id.country_id.code != 'AR':
            return super().create_document_type_sequences()
        if not self.type == 'sale':
            return False
        if not self.l10n_latam_use_documents:
            return False

        sequences = self.l10n_ar_sequence_ids
        if sequences:
            if sequences.filtered(lambda x: x.number_next_actual > 1):
                raise ValidationError(_(
                    'Can not update journal AFIP Configuration when already'
                    ' has validated invoices'))
            else:
                sequences.unlink()

        # Create Sequences
        letters = self.get_journal_letter()
        internal_types = ['invoice', 'debit_note', 'credit_note']
        domain = [
            ('country_id.code', '=', 'AR'),
            ('internal_type', 'in', internal_types),
            '|', ('l10n_ar_letter', '=', False),
            ('l10n_ar_letter', 'in', letters),
        ]
        codes = self.get_journal_codes()
        if codes:
            domain.append(('code', 'in', codes))
        documents = self.env['l10n_latam.document.type'].search(domain)
        sequence_obj = self.env['ir.sequence']
        for document in documents:
            if self.l10n_ar_share_sequences:
                letter_sequence = sequence_obj.search([
                    ('l10n_ar_letter', '=', document.l10n_ar_letter)])
                if letter_sequence:
                    continue

            sequences |= self.env['ir.sequence'].create(
                document.get_document_sequence_vals(self))
        return sequences

    @api.constrains('type', 'l10n_ar_afip_pos_system',
                    'l10n_ar_afip_pos_number', 'l10n_ar_share_sequences')
    def check_sequences(self):
        """ Create / Update the Document Sequences """
        for rec in self.filtered(lambda x: x.type == 'sale'):
            rec.create_document_type_sequences()

    @api.constrains('l10n_ar_afip_pos_number')
    def check_afip_pos_number(self):
        missing_pos_number = self.filtered(
            lambda x: x.type == 'sale' and x.l10n_ar_afip_pos_number == 0)
        if missing_pos_number:
            raise ValidationError(_('Please define a valid AFIP POS number'))

    @api.onchange('l10n_ar_afip_pos_system')
    def _onchange_l10n_ar_afip_pos_system(self):
        """ On 'Factura Pre-impresa' the usual is to share sequences.
        On other types, do not share
        """
        if self.l10n_ar_afip_pos_system == 'II_IM':
            self.l10n_ar_share_sequences = True
        else:
            self.l10n_ar_share_sequences = False
