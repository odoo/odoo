# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.tools import SQL

_DOCUMENTS_MAPPING = {
    "01": [
        'ec_dt_01',
        'ec_dt_02',
        'ec_dt_04',
        'ec_dt_05',
        'ec_dt_08',
        'ec_dt_09',
        'ec_dt_11',
        'ec_dt_12',
        'ec_dt_16',
        'ec_dt_20',
        'ec_dt_21',
        'ec_dt_41',
        'ec_dt_42',
        'ec_dt_43',
        'ec_dt_45',
        'ec_dt_47',
        'ec_dt_48'
    ],
    "02": [
        'ec_dt_03',
        'ec_dt_04',
        'ec_dt_05',
        'ec_dt_09',
        'ec_dt_19',
        'ec_dt_41',
        'ec_dt_294',
        'ec_dt_344'
    ],
    "03": [
        'ec_dt_03',
        'ec_dt_04',
        'ec_dt_05',
        'ec_dt_09',
        'ec_dt_15',
        'ec_dt_19',
        'ec_dt_41',
        'ec_dt_45',
        'ec_dt_294',
        'ec_dt_344'
    ],
    "04": [
        'ec_dt_01',
        'ec_dt_04',
        'ec_dt_05',
        'ec_dt_41',
        'ec_dt_44',
        'ec_dt_47',
        'ec_dt_48',
        'ec_dt_49',
        'ec_dt_50',
        'ec_dt_51',
        'ec_dt_52',
        'ec_dt_370',
        'ec_dt_371',
        'ec_dt_372',
        'ec_dt_373'
    ],
    "05": [
        'ec_dt_01',
        'ec_dt_04',
        'ec_dt_05',
        'ec_dt_41',
        'ec_dt_44',
        'ec_dt_47',
        'ec_dt_48',
        'ec_dt_370',
        'ec_dt_371',
        'ec_dt_372',
        'ec_dt_373'
    ],
    "06": [
        'ec_dt_01',
        'ec_dt_04',
        'ec_dt_05',
        'ec_dt_41',
        'ec_dt_44',
        'ec_dt_47',
        'ec_dt_48',
        'ec_dt_370',
        'ec_dt_371',
        'ec_dt_372',
        'ec_dt_373'
    ],
    "07": [
        'ec_dt_01',
        'ec_dt_04',
        'ec_dt_05',
    ],
    "09": [
        'ec_dt_01',
        'ec_dt_04',
        'ec_dt_05',
        'ec_dt_15',
        'ec_dt_16',
        'ec_dt_41',
        'ec_dt_47',
        'ec_dt_48',
    ],
    "20": [
        'ec_dt_01',
        'ec_dt_04',
        'ec_dt_05',
        'ec_dt_15',
        'ec_dt_16',
        'ec_dt_41',
        'ec_dt_47',
        'ec_dt_48'
    ],
    "21": [
        'ec_dt_01',
        'ec_dt_04',
        'ec_dt_05',
        'ec_dt_15',
        'ec_dt_16',
        'ec_dt_41',
        'ec_dt_47',
        'ec_dt_48'
    ],
}


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_ec_sri_payment_id = fields.Many2one(
        comodel_name="l10n_ec.sri.payment",
        string="Payment Method (SRI)",
        help="Ecuador: Payment Methods Defined by the SRI.",
        default=lambda self: self.env['l10n_ec.sri.payment'].search([], limit=1),
    )

    @api.model
    def _get_l10n_ec_documents_allowed(self, identification_code):
        documents_allowed = self.env['l10n_latam.document.type']
        for document_ref in _DOCUMENTS_MAPPING.get(identification_code, []):
            document_allowed = self.env.ref('l10n_ec.%s' % document_ref, False)
            if document_allowed:
                documents_allowed |= document_allowed
        return documents_allowed

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        domain = super()._get_l10n_latam_documents_domain()
        if self.country_code == 'EC' and self.l10n_latam_use_documents:
            if self.debit_origin_id:  # show/hide the debit note document type
                domain.extend([('internal_type', '=', 'debit_note')])
            elif self.move_type in ('out_invoice', 'in_invoice'):
                domain.extend([('internal_type', '=', 'invoice')])
            allowed_documents = self._get_l10n_ec_documents_allowed(self.partner_id._l10n_ec_get_ats_code(self.move_type))
            domain.extend([('id', 'in', allowed_documents.ids)])
        return domain

    def _get_ec_formatted_sequence(self, number=0):
        return "%s %s-%s-%09d" % (
            self.l10n_latam_document_type_id.doc_code_prefix,
            self.journal_id.l10n_ec_entity,
            self.journal_id.l10n_ec_emission,
            number,
        )

    def _get_starting_sequence(self):
        """If use documents then will create a new starting sequence using the document type code prefix and the
        journal document number with a 8 padding number"""
        if (
            self.l10n_latam_use_documents
            and self.company_id.country_id.code == "EC"
        ):
            if self.l10n_latam_document_type_id:
                return self._get_ec_formatted_sequence()
        return super()._get_starting_sequence()

    def _get_last_sequence_domain(self, relaxed=False):
        condition = super()._get_last_sequence_domain(relaxed)
        if self.country_code == "EC" and self.l10n_latam_use_documents:
            internal_type = self.l10n_latam_document_type_id.internal_type
            document_types = self.env['l10n_latam.document.type'].search([
                ('internal_type', '=', internal_type),
                ('country_id.code', '=', 'EC'),
            ])
            if document_types:
                condition = SQL("%s AND l10n_latam_document_type_id IN %s", condition, tuple(document_types.ids))
        return condition

    def _skip_format_document_number(self):
        """
        If a Credit Note is created from a Vendor Bill and the partner_id != "EC",
        we want to allow the user to allocate any number without following the EC format.
        """
        self.ensure_one()
        if self.country_code == 'EC':
            return (
                    self.l10n_latam_document_type_id.internal_type in ('credit_note', 'debit_note')
                    and self.partner_id.country_code != "EC"
                    and self.move_type == 'in_refund'
                    and self.journal_id.type == 'purchase'
            )
        super()._skip_format_document_number()
