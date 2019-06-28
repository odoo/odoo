# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, RedirectWarning


class AccountJournal(models.Model):

    _inherit = "account.journal"

    l10n_ar_afip_pos_system = fields.Selection(
        selection='_get_l10n_ar_afip_pos_types_selection', string='AFIP POS System')
    l10n_ar_afip_pos_number = fields.Integer(
        'AFIP POS Number', help='This is the point of sale number assigned by AFIP in order to you in order to'
        ' generate invoices')
    l10n_ar_afip_pos_partner_id = fields.Many2one(
        'res.partner', 'AFIP POS Address', help='This is the address used for invoice reports of this POS')
    l10n_ar_sequence_ids = fields.One2many('ir.sequence', 'l10n_latam_journal_id')
    l10n_ar_share_sequences = fields.Boolean(
        'Unified Book', help='Use same sequence for documents with the same letter')

    def _get_l10n_ar_afip_pos_types_selection(self):
        """ Return the list of values of the selection field. """
        # TODO add liquido producto
        return [
            ('II_IM', 'Factura Pre-impresa'),
            ('RLI_RLM', 'Factura en Linea'),
            ('BFERCEL', 'Bonos Fiscales Electrónicos - Factura en Linea'),
            ('FEERCELP', 'Comprobantes de Exportacion - Facturador Plus'),
            ('FEERCEL', 'Comprobantes de Exportacion - Factura en Linea'),
            ('CPERCEL', 'Codificación de Producto - Comprobantes en Línea'),
        ]

    def get_journal_letter(self, counterpart_partner=False):
        """ Regarding the AFIP responsability of the company and the type of journal (sale/purchase), get the allowed
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
                '8': ['I'],
                '9': [],
                '10': [],
                '13': ['C', 'E'],
            },
            'received': {
                '1': ['A', 'C', 'M', 'I'],
                '3': ['B', 'C', 'I'],
                '4': ['B', 'C', 'I'],
                '5': ['B', 'C', 'I'],
                '6': ['B', 'C', 'I'],
                '8': ['E'],
                '9': ['E'],
                '10': ['E'],
                '13': ['B', 'C', 'I'],
            },
        }
        if not self.company_id.l10n_ar_afip_responsability_type_id:
            action = self.env.ref('base.action_res_company_form')
            msg = _(
                'Can not create chart of account until you configure your company AFIP Responsability and VAT.')
            raise RedirectWarning(msg, action.id, _('Go to Companies'))

        letters = letters_data['issued' if self.type == 'sale' else 'received'][
            self.company_id.l10n_ar_afip_responsability_type_id.code]
        if not counterpart_partner:
            return letters

        if not counterpart_partner.l10n_ar_afip_responsability_type_id:
            letters = []
        else:
            counterpart_letters = letters_data['issued' if self.type == 'purchase' else 'received'][
                counterpart_partner.l10n_ar_afip_responsability_type_id.code]
            letters = list(set(letters) & set(counterpart_letters))
        return letters

    def get_journal_codes(self):
        self.ensure_one()
        usual_codes = ['1', '2', '3', '6', '7', '8', '11', '12', '13']
        mipyme_codes = ['201', '202', '203', '206', '207', '208', '211', '212', '213']
        factura_m_codes = ['51', '52', '53']
        receipt_m_code = ['54']
        receipt_codes = ['4', '9', '15']
        expo_codes = ['19', '20', '21']
        if self.type != 'sale':
            return []
        elif self.l10n_ar_afip_pos_system == 'II_IM':
            # factura pre impresa
            return usual_codes + receipt_codes + expo_codes + factura_m_codes + receipt_m_code
        elif self.l10n_ar_afip_pos_system in ['RAW_MAW', 'RLI_RLM']:
            # factura electronica/online
            return usual_codes + receipt_codes + factura_m_codes + receipt_m_code + mipyme_codes
        elif self.l10n_ar_afip_pos_system in ['CPERCEL', 'CPEWS']:
            # factura con detalle
            return usual_codes + factura_m_codes
        elif self.l10n_ar_afip_pos_system in ['BFERCEL', 'BFEWS']:
            # factura bono
            return usual_codes + mipyme_codes
        elif self.l10n_ar_afip_pos_system in ['FEERCEL', 'FEEWS', 'FEERCELP']:
            return expo_codes

    @api.model
    def create(self, values):
        self.new(values).check_afip_configurations()
        return super().create(values)

    @api.multi
    def write(self, values):
        to_check = set(['type', 'l10n_ar_afip_pos_system', 'l10n_ar_afip_pos_number', 'l10n_ar_share_sequences',
                        'l10n_latam_use_documents'])
        if to_check.intersection(set(values.keys())):
            for rec in self:
                rec.check_afip_configurations()
        return super().write(values)

    # TODO make it with https://github.com/odoo/odoo/pull/31059
    def check_afip_configurations(self):
        """ IF AFIP Configuration change try to review if this can be done and then create / update the document
        sequences """
        self.ensure_one()
        if self.company_id.country_id != self.env.ref('base.ar'):
            return True

        invoices = self.env['account.invoice'].search(
            [('journal_id', '=', self.id), ('state', 'in', ['open', 'in_payment', 'paid'])])
        if invoices:
            raise ValidationError(_(
                'You can not change the journal configuration for a journal that already have validate invoices: %s' % (
                    ', '.join(invoices.mapped('display_name')))))

        if not self.type == 'sale':
            return False
        if not self.l10n_latam_use_documents:
            return False

        sequences = self.l10n_ar_sequence_ids
        sequences.unlink()

        # Create Sequences
        letters = self.get_journal_letter()
        internal_types = ['invoice', 'debit_note', 'credit_note']
        domain = [('country_id.code', '=', 'AR'), ('internal_type', 'in', internal_types),
                  '|', ('l10n_ar_letter', '=', False), ('l10n_ar_letter', 'in', letters)]
        codes = self.get_journal_codes()
        if codes:
            domain.append(('code', 'in', codes))
        documents = self.env['l10n_latam.document.type'].search(domain)
        for document in documents:
            if self.l10n_ar_share_sequences and self.l10n_ar_sequence_ids.filtered(
                   lambda x: x.l10n_ar_letter == document.l10n_ar_letter):
                continue

            sequences |= self.env['ir.sequence'].create(document.get_document_sequence_vals(self))
        return sequences

    @api.constrains('l10n_ar_afip_pos_number')
    def check_afip_pos_number(self):
        missing_pos_number = self.filtered(
            lambda x: x.type == 'sale' and x.l10n_latam_use_documents and x.l10n_ar_afip_pos_number == 0)
        if missing_pos_number:
            raise ValidationError(_('Please define a valid AFIP POS number'))

    @api.onchange('l10n_ar_afip_pos_system')
    def _onchange_l10n_ar_afip_pos_system(self):
        """ On 'Factura Pre-impresa' the usual is to share sequences. On other types, do not share """
        self.l10n_ar_share_sequences = bool(self.l10n_ar_afip_pos_system == 'II_IM')

    @api.onchange('company_id')
    def _onchange_company_set_domain(self):
        """ Will define the AFIP POS Address field domain taking into account the company configured in the journal """
        company_partner = self.company_id.partner_id.id
        return {'domain': {'l10n_ar_afip_pos_partner_id': [
            '|', ('id', '=', company_partner), '&', ('id', 'child_of', company_partner), ('type', '!=', 'contact')]}}
