# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning


class AccountJournal(models.Model):
    _inherit = "account.journal"

    l10n_ar_afip_pos_system = fields.Selection(
        selection='_get_l10n_ar_afip_pos_types_selection', string='ARCA POS System',
        compute='_compute_l10n_ar_afip_pos_system', store=True, readonly=False,
        help="Argentina: Specify which type of system will be used to create the electronic invoice. This will depend on the type of invoice to be created.",
    )
    l10n_ar_afip_pos_number = fields.Integer(
        'ARCA POS Number', help='This is the point of sale number assigned by ARCA in order to generate invoices')
    company_partner = fields.Many2one('res.partner', related='company_id.partner_id')
    l10n_ar_afip_pos_partner_id = fields.Many2one(
        'res.partner', 'ARCA POS Address', help='This is the address used for invoice reports of this POS',
        domain="['|', ('id', '=', company_partner), '&', ('id', 'child_of', company_partner), ('type', '!=', 'contact')]"
    )
    l10n_ar_is_pos = fields.Boolean(
        compute="_compute_l10n_ar_is_pos", store=True, readonly=False,
        string="Is ARCA POS?",
        help="Argentina: Specify if this Journal will be used to send electronic invoices to ARCA.",
    )

    @api.depends('country_code', 'type', 'l10n_latam_use_documents')
    def _compute_l10n_ar_is_pos(self):
        for journal in self:
            journal.l10n_ar_is_pos = journal.country_code == 'AR' and journal.type == 'sale' and journal.l10n_latam_use_documents

    @api.depends('l10n_ar_is_pos')
    def _compute_l10n_ar_afip_pos_system(self):
        for journal in self:
            journal.l10n_ar_afip_pos_system = journal.l10n_ar_is_pos and journal.l10n_ar_afip_pos_system

    def _get_l10n_ar_afip_pos_types_selection(self):
        """ Return the list of values of the selection field. """
        return [
            ('II_IM', _('Pre-printed Invoice')),
            ('RLI_RLM', _('Online Invoice')),
            ('BFERCEL', _('Electronic Fiscal Bond - Online Invoice')),
            ('FEERCELP', _('Export Voucher - Billing Plus')),
            ('FEERCEL', _('Export Voucher - Online Invoice')),
            ('CPERCEL', _('Product Coding - Online Voucher')),
            ('CF', _('External Fiscal Controller')),
        ]

    def _get_journal_letter(self, counterpart_partner=False):
        """ Regarding the ARCA responsibility of the company and the type of journal (sale/purchase), get the allowed
        letters. Optionally, receive the counterpart partner (customer/supplier) and get the allowed letters to work
        with him. This method is used to populate document types on journals and also to filter document types on
        specific invoices to/from customer/supplier
        """
        self.ensure_one()
        letters_data = {
            'issued': {
                '1': ['A', 'B', 'E', 'M'],
                '4': ['C'],
                '5': [],
                '6': ['C', 'E'],
                '7': ['B', 'C', 'I'],
                '8': ['I'],
                '9': ['I'],
                '10': [],
                '13': ['C', 'E'],
                '15': [],
                '16': [],
            },
            'received': {
                '1': ['A', 'B', 'C', 'E', 'M', 'I'],
                '4': ['B', 'C', 'I'],
                '5': ['B', 'C', 'I'],
                '6': ['A', 'B', 'C', 'M', 'I'],
                '7': ['B', 'C', 'I'],
                '8': ['E', 'B', 'C'],
                '9': ['E', 'B', 'C'],
                '10': ['E', 'B', 'C'],
                '13': ['A', 'B', 'C', 'M', 'I'],
                '15': ['B', 'C', 'I'],
                '16': ['A', 'C', 'M'],
            },
        }
        if not self.company_id.l10n_ar_afip_responsibility_type_id:
            action = self.env.ref('base.action_res_company_form')
            msg = _('Can not create chart of account until you configure your company ARCA Responsibility and VAT.')
            raise RedirectWarning(msg, action.id, _('Go to Companies'))

        letters = letters_data['issued' if self.l10n_ar_is_pos else 'received'][
            self.company_id.l10n_ar_afip_responsibility_type_id.code]
        if counterpart_partner:
            counterpart_letters = letters_data['issued' if not self.l10n_ar_is_pos else 'received'].get(
                counterpart_partner.l10n_ar_afip_responsibility_type_id.code, [])
            letters = list(set(letters) & set(counterpart_letters))
        return letters

    def _get_journal_codes_domain(self):
        self.ensure_one()
        return self._get_codes_per_journal_type(self.l10n_ar_afip_pos_system)

    @api.model
    def _get_codes_per_journal_type(self, afip_pos_system):
        usual_codes = ['1', '2', '3', '6', '7', '8', '11', '12', '13']
        mipyme_codes = ['201', '202', '203', '206', '207', '208', '211', '212', '213']
        invoice_m_code = ['51', '52', '53']
        receipt_m_code = ['54']
        receipt_codes = ['4', '9', '15']
        expo_codes = ['19', '20', '21']
        tique_codes = ['81', '82', '83', '110', '112', '113', '115', '116', '118', '119', '120']
        lsg_codes = ['331']
        no_pos_docs = [
            '23', '24', '25', '26', '27', '28', '33', '43', '45', '46', '48', '58', '60', '61', '150', '151', '157',
            '158', '161', '162', '164', '166', '167', '171', '172', '180', '182', '186', '188', '332']
        codes = []
        if (self.type == 'sale' and not self.l10n_ar_is_pos) or (self.type == 'purchase' and afip_pos_system in ['II_IM', 'RLI_RLM']):
            codes = no_pos_docs + lsg_codes
        elif self.type == 'purchase' and afip_pos_system == 'RAW_MAW':
            # electronic invoices (wsfev1) (intersection between available docs on ws and no_pos_docs)
            codes = ['60', '61']
        elif self.type == 'purchase':
            return [('code', 'not in', no_pos_docs)]
        elif afip_pos_system == 'II_IM':
            # pre-printed invoice
            codes = usual_codes + receipt_codes + expo_codes + invoice_m_code + receipt_m_code
        elif afip_pos_system in ['RAW_MAW', 'RLI_RLM']:
            # electronic/online invoice
            codes = usual_codes + receipt_codes + invoice_m_code + receipt_m_code + mipyme_codes
        elif afip_pos_system in ['CPERCEL', 'CPEWS']:
            # invoice with detail
            codes = usual_codes + invoice_m_code
        elif afip_pos_system in ['BFERCEL', 'BFEWS']:
            # Bonds invoice
            codes = usual_codes + mipyme_codes
        elif afip_pos_system in ['FEERCEL', 'FEEWS', 'FEERCELP']:
            codes = expo_codes
        elif afip_pos_system == 'CF':
            codes = tique_codes
        return [('code', 'in', codes)]

    @api.constrains('l10n_ar_afip_pos_system')
    def _check_afip_pos_system(self):
        journals = self.filtered(
            lambda j: j.l10n_ar_is_pos and j.type == 'purchase' and
            j.l10n_ar_afip_pos_system not in ['II_IM', 'RLI_RLM', 'RAW_MAW'])
        if journals:
            raise ValidationError("\n".join(
                _("The pos system %(system)s can not be used on a purchase journal (id %(id)s)", system=x.l10n_ar_afip_pos_system, id=x.id)
                for x in journals
            ))

    @api.constrains('l10n_ar_afip_pos_number')
    def _check_afip_pos_number(self):
        if self.filtered(lambda j: j.l10n_ar_is_pos and j.l10n_ar_afip_pos_number == 0):
            raise ValidationError(_('Please define an ARCA POS number'))

        if self.filtered(lambda j: j.l10n_ar_is_pos and j.l10n_ar_afip_pos_number > 99999):
            raise ValidationError(_('Please define a valid ARCA POS number (5 digits max)'))

    @api.onchange('l10n_ar_afip_pos_number', 'type')
    def _onchange_set_short_name(self):
        """ Will define the ARCA POS Address field domain taking into account the company configured in the journal
        The short code of the journal only admit 5 characters, so depending on the size of the pos_number (also max 5)
        we add or not a prefix to identify sales journal.
        """
        if self.type == 'sale' and self.l10n_ar_afip_pos_number:
            self.code = "%05i" % self.l10n_ar_afip_pos_number

    def write(self, vals):
        protected_fields = ('type', 'l10n_ar_afip_pos_system', 'l10n_ar_afip_pos_number', 'l10n_latam_use_documents')
        fields_to_check = [field for field in protected_fields if field in vals]

        if fields_to_check:
            self.env.cr.execute("SELECT DISTINCT(journal_id) FROM account_move WHERE posted_before = True")
            res = self.env.cr.fetchall()
            journal_with_entry_ids = [journal_id for journal_id, in res]

            for journal in self:
                if (
                    journal.company_id.account_fiscal_country_id.code != "AR"
                    or journal.type not in ['sale', 'purchase']
                    or journal.id not in journal_with_entry_ids
                ):
                    continue

                for field in fields_to_check:
                    # Wouldn't work if there was a relational field, as we would compare an id with a recordset.
                    if vals[field] != journal[field]:
                        raise UserError(_("You can not change %s journal's configuration if it already has validated invoices", journal.name))

        return super().write(vals)
