from odoo import fields, models


class ZatcaMixin(models.AbstractModel):
    """The point of this class is to hold common properties between models that should be sent to zatca"""

    _inherit = "zatca.mixin"

    l10n_sa_edi_supply_end_date = fields.Date(string="Supply End Date", copy=False, help="Date when the supply of goods or services is completed, mainly used for continuous supplies.")
    l10n_sa_uuid = fields.Char(string='Document UUID (SA)', copy=False, help="Universally unique identifier of the Invoice")
    l10n_sa_invoice_signature = fields.Char("Unsigned XML Signature", copy=False)
    l10n_sa_edi_document_id = fields.Many2one(comodel_name="l10n_sa_edi.document", copy=False)
    l10n_sa_edi_state = fields.Selection(related="l10n_sa_edi_document_id.state")
    l10n_sa_chain_index = fields.Integer(related="l10n_sa_edi_document_id.l10n_sa_chain_index")

    def _l10n_sa_get_alerts(self):
        return {}

    def _l10n_sa_handle_alerts(self):
        raise NotImplementedError

    def _l10n_sa_get_adjustment_reason(self):
        self.ensure_one()
        readable_zatca_reason = dict(self._fields['l10n_sa_reason'].selection).get(self.l10n_sa_reason)
        return readable_zatca_reason if self.l10n_sa_show_reason else self.ref

    def _l10n_sa_build_qr(self):
        self.ensure_one()
        if self._l10n_sa_is_phase_2_applicable():
            return self.l10n_sa_edi_document_id._l10n_sa_get_phase_2_qr(self.l10n_sa_invoice_type == 'simplified')
        return super()._l10n_sa_build_qr()

    def _l10n_sa_get_payment_means_code(self):
        """
        Get ZATCA payment means code.

        This is a template method that should be overridden in implementing classes
        to provide specific payment means logic for invoices vs POS orders.

        :return: str - Payment means code key (cash/card/bank/transfer/unknown)
        """
        # Default implementation - should be overridden
        return 'unknown'

    def _get_l10n_sa_journal(self):
        return self.env['account.journal']

    def _l10n_sa_edi_create_document(self):
        self.ensure_one()
        if self.l10n_sa_edi_state != 'rejected' and self.l10n_sa_edi_document_id:
            return
        self.l10n_sa_edi_document_id = self.env['l10n_sa_edi.document'].create({
            'res_id': self.id,
            'res_model': self._name,
            'company_id': self.company_id.id,
            'journal_id': self._get_l10n_sa_journal().id,
            'state': 'to_send',
        })

    def _l10n_sa_generate_zatca_template(self):
        """Render the ZATCA UBL file, To be overriden"""
        return ''
