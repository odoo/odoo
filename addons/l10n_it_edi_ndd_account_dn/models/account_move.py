from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_it_edi_features_for_document_type_selection(self):
        # EXTENDS 'l10n_it_edi'
        document_type_features = super()._l10n_it_edi_features_for_document_type_selection()
        if self.debit_origin_id:
            document_type_features['debit_note'] = True
        return document_type_features

    def _l10n_it_edi_document_type_mapping(self):
        # EXTENDS 'l10n_it_edi'
        document_type_mapping = super()._l10n_it_edi_document_type_mapping()
        document_type_mapping['TD01']['debit_note'] = False
        document_type_mapping['TD05']['debit_note'] = True
        return document_type_mapping
