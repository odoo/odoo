# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api
from odoo.addons.l10n_ec.models.res_partner import verify_final_consumer

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
        'ec_dt_04',
        'ec_dt_05',
        'ec_dt_18',
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
        'ec_dt_04',
        'ec_dt_05',
        'ec_dt_18',
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
        'ec_dt_04',
        'ec_dt_05',
        'ec_dt_18',
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
        'ec_dt_04',
        'ec_dt_05',
        'ec_dt_18'
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
    )

    def _get_l10n_ec_identification_type(self):
        self.ensure_one()
        move = self
        it_ruc = self.env.ref("l10n_ec.ec_ruc", False)
        it_dni = self.env.ref("l10n_ec.ec_dni", False)
        it_passport = self.env.ref("l10n_ec.ec_passport", False)
        is_final_consumer = verify_final_consumer(move.partner_id.commercial_partner_id.vat)
        is_ruc = move.partner_id.commercial_partner_id.l10n_latam_identification_type_id.id == it_ruc.id
        is_dni = move.partner_id.commercial_partner_id.l10n_latam_identification_type_id.id == it_dni.id
        is_passport = move.partner_id.commercial_partner_id.l10n_latam_identification_type_id.id == it_passport.id
        l10n_ec_is_exportation = move.partner_id.commercial_partner_id.country_id.code != 'EC'
        identification_code = False
        if move.move_type in ("in_invoice", "in_refund"):
            if is_ruc:
                identification_code = "01"
            elif is_dni:
                identification_code = "02"
            else:
                identification_code = "03"
        elif move.move_type in ("out_invoice", "out_refund"):
            if not l10n_ec_is_exportation:
                if is_final_consumer:
                    identification_code = "07"
                elif is_ruc:
                    identification_code = "04"
                elif is_dni:
                    identification_code = "05"
                elif is_passport:
                    identification_code = "06"
            else:
                if is_ruc:
                    identification_code = "20"
                elif is_dni:
                    identification_code = "21"
                else:
                    identification_code = "09"
        return identification_code

    @api.model
    def _get_l10n_ec_documents_allowed(self, identification_code):
        documents_allowed = self.env['l10n_latam.document.type']
        for document_ref in _DOCUMENTS_MAPPING.get(identification_code, []):
            document_allowed = self.env.ref('l10n_ec.%s' % document_ref, False)
            if document_allowed:
                documents_allowed |= document_allowed
        return documents_allowed

    def _get_l10n_ec_internal_type(self):
        self.ensure_one()
        internal_type = self.env.context.get("internal_type", "invoice")
        if self.move_type in ("out_refund", "in_refund"):
            internal_type = "credit_note"
        if self.debit_origin_id:
            internal_type = "debit_note"
        return internal_type

    def _get_l10n_latam_documents_domain(self):
        self.ensure_one()
        if self.journal_id.company_id.account_fiscal_country_id != self.env.ref('base.ec') or not \
                self.journal_id.l10n_latam_use_documents:
            return super()._get_l10n_latam_documents_domain()
        domain = [
            ('country_id.code', '=', 'EC'),
            ('internal_type', 'in', ['invoice', 'debit_note', 'credit_note', 'invoice_in'])
        ]
        internal_type = self._get_l10n_ec_internal_type()
        allowed_documents = self._get_l10n_ec_documents_allowed(self._get_l10n_ec_identification_type())
        if internal_type and allowed_documents:
            domain.append(("id", "in", allowed_documents.filtered(lambda x: x.internal_type == internal_type).ids))
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
            self.journal_id.l10n_latam_use_documents
            and self.company_id.country_id.code == "EC"
        ):
            if self.l10n_latam_document_type_id:
                return self._get_ec_formatted_sequence()
        return super()._get_starting_sequence()

    def _get_last_sequence_domain(self, relaxed=False):
        l10n_latam_document_type_model = self.env['l10n_latam.document.type']
        where_string, param = super(AccountMove, self)._get_last_sequence_domain(relaxed)
        if self.country_code == "EC" and self.l10n_latam_use_documents and self.move_type in (
            "out_invoice",
            "out_refund",
            "in_invoice",
            "in_refund",
        ):
            where_string, param = super(AccountMove, self)._get_last_sequence_domain(False)
            internal_type = self._get_l10n_ec_internal_type()
            document_types = l10n_latam_document_type_model.search([
                ('internal_type', '=', internal_type),
                ('country_id.code', '=', 'EC'),
            ])
            if document_types:
                where_string += """
                AND l10n_latam_document_type_id in %(l10n_latam_document_type_id)s
                """
                param["l10n_latam_document_type_id"] = tuple(document_types.ids)
        return where_string, param
