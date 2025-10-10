from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    peppol_contract_document_reference = fields.Char(string="Contract Reference")
    peppol_originator_document_reference = fields.Char(string="Originator Reference")
    peppol_despatch_document_reference = fields.Char(string="Despatch Reference")
    peppol_additional_document_reference = fields.Char(string="Additional Reference")

    ubl_cii_xml_filename = fields.Char(compute=False)
    enable_ubl_cii_xml_file = fields.Boolean(compute='_compute_enable_ubl_cii_xml_file')

    def _compute_filename(self):
        # OVERRIDE account_edi_ubl_cii
        # To be removed in master
        pass

    def _compute_enable_ubl_cii_xml_file(self):
        for move in self:
            move.enable_ubl_cii_xml_file = move.journal_id.type != 'purchase' if move.journal_id else False
