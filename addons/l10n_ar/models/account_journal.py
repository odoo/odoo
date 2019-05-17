# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


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

    def get_journal_letter(self, counterpart_partner=False):
        self.ensure_one()
        return self._get_journal_letter(
            journal_type=self.type,
            company=self.company_id,
            counterpart_partner=counterpart_partner)

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
        # TODO mover a otro lado este dict
        letters_data = {
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
        if self.type == 'purchase':
            return ['19']
        elif self.l10n_ar_afip_pos_system in ['RAW_MAW', 'RLI_RLM', 'II_IM']:
            return usual_codes + receipt_codes
        elif self.l10n_ar_afip_pos_system in ['BFERCEL', 'BFEWS']:
            return usual_codes
        elif self.l10n_ar_afip_pos_system in ['FEERCEL', 'FEEWS', 'FEERCELP']:
            return expo_codes
