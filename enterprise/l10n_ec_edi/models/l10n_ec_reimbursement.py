# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.l10n_ec.models.res_partner import PartnerIdTypeEc
from odoo.addons.l10n_ec_edi.models.account_move import L10N_EC_VAT_SUBTAXES, L10N_EC_VAT_RATES
from odoo.exceptions import UserError
from odoo.tools import float_repr
from odoo.addons.l10n_ec.models.res_partner import verify_final_consumer
import re


class L10nEcReimbursement(models.Model):
    '''
    This class allow to store the purchase invoice related with reimbursements in client scenario
    '''
    _name = 'l10n_ec.reimbursement'
    _description = 'Reimbursement Lines'

    # Columns
    move_id = fields.Many2one(
        'account.move',
        required=True,
        string='Invoice',
        ondelete='cascade'
    )
    company_id = fields.Many2one(
        related="move_id.company_id"
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        help='The partner associated to the purchase document'
    )
    partner_vat_number = fields.Char(
        string='Vat Number',
        required=True,
        help='The partner vat number that will be showed in EDI and ATS'
    )
    partner_vat_type_id = fields.Many2one(
        'l10n_latam.identification.type',
        string="Vat Type",
        required=True,
        domain=lambda self: [('id', 'in', [self.env.ref('l10n_ec.ec_ruc').id, self.env.ref('l10n_latam_base.it_vat').id])]
    )
    partner_country_id = fields.Many2one(
        'res.country',
        string='Country',
        required=True,
    )
    partner_country_code = fields.Char(
        related='partner_country_id.code',
    )
    l10n_latam_document_type_id = fields.Many2one(
        'l10n_latam.document.type',
        string='Document Type',
        required=True,
    )
    document_number = fields.Char(
        string='Document number',
        size=17,
        required=True,
    )
    authorization_number = fields.Char(
        string='Authorization number',
        help='Authorization number for issuing the tributary document, assigned by SRI, can be 10 numbers long, 41, or 49.'
    )
    date = fields.Date(
        string='Date',
        required=True,
    )
    currency_id = fields.Many2one(
        related='move_id.currency_id',
    )
    tax_id = fields.Many2one(
        'account.tax',
        string="Tax",
        required=True,
        domain=lambda self: [("type_tax_use", "=", 'purchase')]
    )
    tax_base = fields.Monetary(
        string='Tax Base',
        currency_field="currency_id",
        help='The VAT taxable amount (whether VAT 15%, VAT 5% or other percentages) can be found in the subtotal of the purchase invoice.'
    )
    tax_amount = fields.Monetary(
        string='Tax Value',
        currency_field="currency_id",
        compute='_compute_tax_amount',
        readonly=False,
        store=True,
        help='The tax value of purchase invoice.It\'s editable because could be unbalanced by decimals'
    )
    total = fields.Monetary(
        string='Total',
        currency_field="currency_id",
        compute='_compute_total',
        store=True,
        readonly=True
    )

    # ===== COMPUTE / ONCHANGE / CONSTRAINTS METHODS =====

    @api.onchange('authorization_number')
    def onchange_authorization_number(self):
        """ When the authorization change, populate the number for the document """
        if len(self.authorization_number or '') == 49:
            access_key_fields = self.move_id._l10n_ec_extract_data_from_access_key(authorization_number=self.authorization_number)
            self.partner_id = access_key_fields['partner_id']
            self.document_number = access_key_fields['document_number']
            self.l10n_latam_document_type_id = access_key_fields['l10n_latam_document_type_id']
            self.date = access_key_fields['document_date']
            self.partner_vat_number = access_key_fields['partner_vat']
            self.partner_country_id = access_key_fields['partner_vat'] and self.env['res.country'].search([('code', '=', 'EC')], limit=1).id
            self.partner_vat_type_id = access_key_fields['partner_vat'] and self.env.ref('l10n_ec.ec_ruc', raise_if_not_found=False)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """ When the authorization change, populate the number for the document """
        if self.partner_id:
            self.partner_vat_number = self.partner_id.vat
            self.partner_country_id = self.partner_id.country_id
            if self.partner_id.l10n_latam_identification_type_id in [self.env.ref('l10n_ec.ec_ruc', False), self.env.ref('l10n_latam_base.it_vat', False)]:
                self.partner_vat_type_id = self.partner_id.l10n_latam_identification_type_id
            else:
                self.partner_vat_type_id = False

    def _prepare_base_line_for_taxes_computation(self):
        return self.env['account.tax']._prepare_base_line_for_taxes_computation(
            self,
            tax_ids=self.tax_id,
            price_unit=self.tax_base,
            quantity=1,
            currency_id=self.move_id.currency_id,
        )

    def _get_tax_amounts_converted(self, amount):
        # Convert reimbursement values to show in EDI and ATS
        if self.currency_id != self.company_id.currency_id and self.move_id.invoice_currency_rate:
            amount = self.company_id.currency_id.round(amount / self.move_id.invoice_currency_rate)
        return amount

    @api.depends('tax_base', 'tax_id')
    def _compute_tax_amount(self):
        for move in self:
            if move.tax_id:
                tax_amount = move.tax_id.compute_all(move.tax_base, currency=self.currency_id, quantity=1.0)
                move.tax_amount = tax_amount['taxes'][0]['amount']  # there can only be one tax

    @api.depends('tax_base', 'tax_id', 'tax_amount')
    def _compute_total(self):
        for move in self:
            if move.tax_id:
                move.total = move.tax_base + move.tax_amount

    @api.onchange('document_number')
    def onchange_l10n_ec_reimbursement_document_number(self):
        # Use the format internal number in case the user change this number
        if self.l10n_latam_document_type_id:
            doc_number = self.l10n_latam_document_type_id._format_document_number(self.document_number)
            if self.document_number != doc_number:
                self.document_number = doc_number

    def _get_reimbursement_partner_identification_type(self):
        """
        Get identification type from the partner. "Table 6 - SRI Technical Sheet"
        """
        self.ensure_one()

        def _get_ats_code_identification_type(partner_type_id):
            if partner_type_id == 'ruc':
                return PartnerIdTypeEc.OUT_RUC.value
            return PartnerIdTypeEc.FOREIGN.value

        partner_type_id = self._get_identification_type()
        if verify_final_consumer(self.partner_vat_number):  # Verify whether the doc number is: 13 * '9'
            code = PartnerIdTypeEc.FINAL_CONSUMER.value
        else:
            code = _get_ats_code_identification_type(partner_type_id)
        return code

    def _get_identification_type(self):
        """Maps Odoo identification types to Ecuadorian ones. In reimbursements can be only ruc or vat"""
        id_type_xmlid = False
        identification_type_id = self.partner_vat_type_id
        if identification_type_id.id == self.env.ref('l10n_ec.ec_ruc').id:
            id_type_xmlid = 'ruc'
        elif identification_type_id.id == self.env.ref('l10n_latam_base.it_vat').id or identification_type_id.country_id.code != 'EC':
            id_type_xmlid = 'foreign'

        return id_type_xmlid

    def _get_reimbursement_line_vals(self):
        # in order to use in EDI
        self.ensure_one()

        def _l10n_ec_get_number_vals(number):
            estab, emision, sequential = '999', '999', number
            num_match = re.match(r'(\d{1,3})-(\d{1,3})-(\d{1,9})', number.strip())
            if num_match:
                estab, emision, sequential = num_match.groups()
            return [estab.zfill(3), emision.zfill(3), sequential.zfill(9)]

        number_reimbursement = _l10n_ec_get_number_vals(self.document_number)
        return {
            'entity_number': number_reimbursement[0],
            'emission_number': number_reimbursement[1],
            'doc_number': number_reimbursement[2],
            'tax_reimbursement_vals': self._get_reimbursement_line_tax_vals()
        }

    def _get_reimbursement_line_tax_vals(self):
        # Return a list of tuple with reimbursements tax info. This is used in Edi
        self.ensure_one()
        tax_dict = {}
        # The info: ('<codigo de impuesto>', '<código de porcentaje del impuesto>', '<tarifa>', <base imponible>, <impuesto del reembolso>)
        if self.tax_base:
            vat_tax = L10N_EC_VAT_RATES[L10N_EC_VAT_SUBTAXES[self.tax_id.tax_group_id.l10n_ec_type]]
            code_percent = next(iter([code for code, val in L10N_EC_VAT_RATES.items() if val == vat_tax]))
            tax_dict = {
                'code': '2',  # Tax code '2' because is 'IVA' (ICE and IRBPNR are not supported yet)
                'code_percent': code_percent,
                'vat_tax': float_repr(vat_tax, 0),
                'tax_base': self._get_tax_amounts_converted(self.tax_base),
                'tax_amount': self._get_tax_amounts_converted(self.tax_amount),
            }
        return tax_dict

    @api.constrains("document_number", "tax_id", "partner_vat_number")
    def _check_duplicated_reimbursement_lines(self):
        for reimburs in self.move_id.l10n_ec_reimbursement_ids:
            if self.move_id.l10n_ec_reimbursement_ids.filtered(
                    lambda r: r.id != reimburs.id and
                          r.tax_id == reimburs.tax_id and
                          r.document_number == reimburs.document_number and
                          r.partner_vat_number == reimburs.partner_vat_number):
                raise UserError(
                    _("You cannot create reimbursements with document number, tax group and partner "
                      "duplicated in the same invoice."))
