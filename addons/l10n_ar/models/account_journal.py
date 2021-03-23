# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, RedirectWarning


class AccountJournal(models.Model):

    _inherit = "account.journal"

    l10n_ar_afip_pos_system = fields.Selection(
        selection='_get_l10n_ar_afip_pos_types_selection', string='AFIP POS System')
    l10n_ar_afip_pos_number = fields.Integer(
        'AFIP POS Number', help='This is the point of sale number assigned by AFIP in order to generate invoices')
    company_partner = fields.Many2one('res.partner', related='company_id.partner_id')
    l10n_ar_afip_pos_partner_id = fields.Many2one(
        'res.partner', 'AFIP POS Address', help='This is the address used for invoice reports of this POS',
        domain="['|', ('id', '=', company_partner), '&', ('id', 'child_of', company_partner), ('type', '!=', 'contact')]"
    )
    l10n_ar_share_sequences = fields.Boolean(
        'Unified Book', help='Use same sequence for documents with the same letter')

    def _get_l10n_ar_afip_pos_types_selection(self):
        """ Return the list of values of the selection field. """
        return [
            ('II_IM', _('Pre-printed Invoice')),
            ('RLI_RLM', _('Online Invoice')),
            ('BFERCEL', _('Electronic Fiscal Bond - Online Invoice')),
            ('FEERCELP', _('Export Voucher - Billing Plus')),
            ('FEERCEL', _('Export Voucher - Online Invoice')),
            ('CPERCEL', _('Product Coding - Online Voucher')),
        ]

    def _get_journal_letter(self, counterpart_partner=False):
        """ Regarding the AFIP responsibility of the company and the type of journal (sale/purchase), get the allowed
        letters. Optionally, receive the counterpart partner (customer/supplier) and get the allowed letters to work
        with him. This method is used to populate document types on journals and also to filter document types on
        specific invoices to/from customer/supplier
        """
        self.ensure_one()
        letters_data = {
            'issued': {
                '1': ['A', 'B', 'E', 'M'],
                '3': [],
                '4': ['C'],
                '5': [],
                '6': ['C', 'E'],
                '9': ['I'],
                '10': [],
                '13': ['C', 'E'],
                '99': []
            },
            'received': {
                '1': ['A', 'B', 'C', 'M', 'I'],
                '3': ['B', 'C', 'I'],
                '4': ['B', 'C', 'I'],
                '5': ['B', 'C', 'I'],
                '6': ['B', 'C', 'I'],
                '9': ['E'],
                '10': ['E'],
                '13': ['B', 'C', 'I'],
                '99': ['B', 'C', 'I']
            },
        }
        if not self.company_id.l10n_ar_afip_responsibility_type_id:
            action = self.env.ref('base.action_res_company_form')
            msg = _('Can not create chart of account until you configure your company AFIP Responsibility and VAT.')
            raise RedirectWarning(msg, action.id, _('Go to Companies'))

        letters = letters_data['issued' if self.type == 'sale' else 'received'][
            self.company_id.l10n_ar_afip_responsibility_type_id.code]
        if counterpart_partner:
            counterpart_letters = letters_data['issued' if self.type == 'purchase' else 'received'].get(
                counterpart_partner.l10n_ar_afip_responsibility_type_id.code, [])
            letters = list(set(letters) & set(counterpart_letters))
        return letters

    def _get_journal_codes(self):
        self.ensure_one()
        usual_codes = ['1', '2', '3', '6', '7', '8', '11', '12', '13']
        mipyme_codes = ['201', '202', '203', '206', '207', '208', '211', '212', '213']
        invoice_m_code = ['51', '52', '53']
        receipt_m_code = ['54']
        receipt_codes = ['4', '9', '15']
        expo_codes = ['19', '20', '21']
        if self.type != 'sale':
            return []
        elif self.l10n_ar_afip_pos_system == 'II_IM':
            # pre-printed invoice
            return usual_codes + receipt_codes + expo_codes + invoice_m_code + receipt_m_code
        elif self.l10n_ar_afip_pos_system in ['RAW_MAW', 'RLI_RLM']:
            # electronic/online invoice
            return usual_codes + receipt_codes + invoice_m_code + receipt_m_code + mipyme_codes
        elif self.l10n_ar_afip_pos_system in ['CPERCEL', 'CPEWS']:
            # invoice with detail
            return usual_codes + invoice_m_code
        elif self.l10n_ar_afip_pos_system in ['BFERCEL', 'BFEWS']:
            # Bonds invoice
            return usual_codes + mipyme_codes
        elif self.l10n_ar_afip_pos_system in ['FEERCEL', 'FEEWS', 'FEERCELP']:
            return expo_codes

    @api.constrains('type', 'l10n_ar_afip_pos_system', 'l10n_ar_afip_pos_number', 'l10n_ar_share_sequences',
                    'l10n_latam_use_documents')
    def _check_afip_configurations(self):
        """ Do not let the user update the journal if it already contains confirmed invoices """
        journals = self.filtered(lambda x: x.company_id.country_id.code == "AR" and x.type in ['sale', 'purchase'])
        invoices = self.env['account.move'].search([('journal_id', 'in', journals.ids), ('posted_before', '=', True)], limit=1)
        if invoices:
            raise ValidationError(
                _("You can not change the journal's configuration if it already has validated invoices") + ' ('
                + ', '.join(invoices.mapped('journal_id').mapped('name')) + ')')

    @api.constrains('l10n_ar_afip_pos_number')
    def _check_afip_pos_number(self):
        to_review = self.filtered(
            lambda x: x.type == 'sale' and x.l10n_latam_use_documents and
            x.company_id.country_id.code == "AR")

        if to_review.filtered(lambda x: x.l10n_ar_afip_pos_number == 0):
            raise ValidationError(_('Please define an AFIP POS number'))

        if to_review.filtered(lambda x: x.l10n_ar_afip_pos_number > 99999):
            raise ValidationError(_('Please define a valid AFIP POS number (5 digits max)'))

    @api.onchange('l10n_ar_afip_pos_system')
    def _onchange_l10n_ar_afip_pos_system(self):
        """ On 'Pre-printed Invoice' the usual is to share sequences. On other types, do not share """
        self.l10n_ar_share_sequences = bool(self.l10n_ar_afip_pos_system == 'II_IM')

    @api.onchange('l10n_ar_afip_pos_number', 'type')
    def _onchange_set_short_name(self):
        """ Will define the AFIP POS Address field domain taking into account the company configured in the journal
        The short code of the journal only admit 5 characters, so depending on the size of the pos_number (also max 5)
        we add or not a prefix to identify sales journal.
        """
        if self.type == 'sale' and self.l10n_ar_afip_pos_number:
            self.code = "%05i" % self.l10n_ar_afip_pos_number
