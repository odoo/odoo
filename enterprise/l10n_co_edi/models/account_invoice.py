# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import textwrap

from odoo import api, models, fields, _
from odoo.exceptions import UserError


DESCRIPTION_CREDIT_CODE = [
    ("1", "Devolución parcial de los bienes y/o no aceptación parcial del servicio"),
    ("2", "Anulación de factura electrónica"),
    ("3", "Rebaja total aplicada"),
    ("4", "Ajuste de precio"),
    ("5", "Descuento comercial por pronto pago"),
    ("6", "Descuento comercial por volumen de ventas")
]

DESCRIPTION_DEBIT_CODE = [
    ('1', 'Intereses'),
    ('2', 'Gastos por cobrar'),
    ('3', 'Cambio del valor'),
    ('4', 'Otros'),
]

L10N_CO_EDI_TYPE = {
    'Sales Invoice': '1',
    'Export Invoice': '2',
    'Electronic transmission document - type 03': '3',
    'Electronic Sales Invoice - type 04': '4',
    'Credit Note': '91',
    'Debit Note': '92',
    'Event (Application Response)': '96',
}


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_co_edi_type = fields.Selection(
        selection=[(code, label) for label, code in L10N_CO_EDI_TYPE.items()],
        compute='_compute_l10n_co_edi_type',
        store=True,
        string='Electronic Invoice Type',
    )
    l10n_co_edi_attachment_url = fields.Char('Electronic Invoice Attachment URL',
                                             help='''Will be included in electronic invoice and can point to
                                             e.g. a ZIP containing additional information about the invoice.''', copy=False)
    l10n_co_edi_operation_type = fields.Selection([('10', 'Estandar'),
                                                  ('09', 'AIU'),
                                                  ('11', 'Mandatos'),
                                                  ('12', 'Transporte'),
                                                  ('13', 'Cambiario'),
                                                  ('15', 'Compra Divisas'),
                                                  ('16', 'Venta Divisas'),
                                                  ('20', 'Nota Crédito que referencia una factura electrónica'),
                                                  ('22', 'Nota Crédito sin referencia a facturas'),
                                                  ('23', 'Nota Crédito para facturación electrónica V1 (Decreto 2242)'),
                                                  ('30', 'Nota Débito que referencia una factura electrónica'),
                                                  ('32', 'Nota Débito sin referencia a facturas'),
                                                  ('23', 'Inactivo: Nota Crédito para facturación electrónica V1 (Decreto 2242)'),
                                                  ('33', 'Inactivo: Nota Débito para facturación electrónica V1 (Decreto 2242)')],
                                                  string="Operation Type (CO)", compute='_compute_operation_type', default="10", required=True)

    # field used to track the status of a submission
    l10n_co_edi_transaction = fields.Char('Transaction ID (CO)', copy=False)
    l10n_co_edi_cufe_cude_ref = fields.Char(string="CUFE/CUDE", copy=False, help='Unique ID received by the government when the invoice is signed.')
    l10n_co_edi_payment_option_id = fields.Many2one('l10n_co_edi.payment.option', string="Payment Option",
                                                    default=lambda self: self.env.ref('l10n_co_edi.payment_option_1', raise_if_not_found=False))
    l10n_co_edi_is_direct_payment = fields.Boolean("Direct Payment from Colombia", compute="_compute_l10n_co_edi_is_direct_payment")
    l10n_co_edi_description_code_credit = fields.Selection(DESCRIPTION_CREDIT_CODE, string="Concepto Nota de Credito")
    l10n_co_edi_description_code_debit = fields.Selection(DESCRIPTION_DEBIT_CODE, string="Concepto Nota de Débito")
    l10n_co_edi_debit_note = fields.Boolean(related="journal_id.l10n_co_edi_debit_note")
    l10n_co_edi_is_support_document = fields.Boolean('Support Document', related='journal_id.l10n_co_edi_is_support_document')

    # -------------------------------------------------------------------------
    # Compute
    # -------------------------------------------------------------------------

    @api.depends('move_type', 'l10n_co_edi_debit_note')
    def _compute_l10n_co_edi_type(self):
        CO_moves = self.filtered(lambda move: move.company_id.account_fiscal_country_id.code == 'CO')
        for move in CO_moves:
            if move.move_type == 'out_refund':
                move.l10n_co_edi_type = L10N_CO_EDI_TYPE['Credit Note']
            elif move.l10n_co_edi_debit_note:
                move.l10n_co_edi_type = L10N_CO_EDI_TYPE['Debit Note']
            elif not move.l10n_co_edi_type:
                move.l10n_co_edi_type = L10N_CO_EDI_TYPE['Sales Invoice']

    @api.depends('move_type', 'reversed_entry_id', 'edi_document_ids.state', 'l10n_co_edi_cufe_cude_ref')
    def _compute_operation_type(self):
        for move in self:
            operation_type = '10'
            if move.move_type == 'out_refund':
                operation_type = '20' if move.reversed_entry_id else '22'
            elif move.l10n_co_edi_debit_note:
                operation_type = '30' if move.debit_origin_id else '32'
            move.l10n_co_edi_operation_type = operation_type

    @api.depends('invoice_date_due', 'date')
    def _compute_l10n_co_edi_is_direct_payment(self):
        for rec in self:
            rec.l10n_co_edi_is_direct_payment = (rec.date == rec.invoice_date_due) and rec.company_id.account_fiscal_country_id.code == 'CO'

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _l10n_co_edi_get_electronic_invoice_type(self):
        if self.move_type == 'out_invoice':
            return 'ND' if self.l10n_co_edi_debit_note else 'INVOIC'
        elif self.move_type == 'in_invoice':
            return 'INVOIC'
        return 'NC'

    def _l10n_co_edi_get_electronic_invoice_type_info(self):
        if self.move_type == 'out_invoice':
            return 'DIAN 2.1: Nota Débito de Factura Electrónica de Venta' if self.l10n_co_edi_debit_note else 'DIAN 2.1: Factura Electrónica de Venta'
        elif self.move_type == 'in_invoice':
            return 'DIAN 2.1: documento soporte en adquisiciones efectuadas a no obligados a facturar.'
        elif self.move_type == 'in_refund':
            return 'DIAN 2.1: Nota de ajuste al documento soporte en adquisiciones efectuadas a sujetos no obligados a expedir factura o documento equivalente'
        return 'DIAN 2.1: Nota Crédito de Factura Electrónica de Venta'

    # -------------------------------------------------------------------------
    # Account_edi OVERRIDE
    # -------------------------------------------------------------------------

    def _retry_edi_documents_error_hook(self):
        # OVERRIDE
        # For CO, remove the l10n_co_edi_transaction to force re-send (otherwise this only triggers a check_status)
        carvajal = self.env.ref('l10n_co_edi.edi_carvajal')
        self.filtered(lambda m: m._get_edi_document(carvajal).blocking_level == 'error').l10n_co_edi_transaction = None

    def button_draft(self):
        # OVERRIDE
        for move in self:
            if move.l10n_co_edi_transaction:
                raise UserError(_(
                    "You can't edit the following journal entry %s because an electronic document has already been "
                    "sent to Carvajal. To edit this entry, you need to create a Credit Note for the invoice and "
                    "create a new invoice.",
                    move.display_name))

        return super().button_draft()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _l10n_co_edi_get_product_code(self):
        """
        For identifying products, different standards can be used.  If there is a barcode, we take that one, because
        normally in the GTIN standard it will be the most specific one.  Otherwise, we will check the
        :return: (standard, product_code)
        """
        self.ensure_one()
        if self.product_id:
            if self.move_id.l10n_co_edi_type == L10N_CO_EDI_TYPE['Export Invoice']:
                if not self.product_id.l10n_co_edi_customs_code:
                    raise UserError(_('Exportation invoices require custom code in all the products, please fill in this information before validating the invoice'))
                return (self.product_id.l10n_co_edi_customs_code, '020', 'Partida Alanceraria')
            if (
                    self.move_type == "in_refund" and
                    self.move_id.l10n_co_edi_is_support_document and
                    (code := self.product_id.default_code or self.product_id.barcode or self.product_id.unspsc_code_id.code)
            ):
                return (code, '999', 'Estándar de adopción del contribuyente')
            elif self.product_id.barcode:
                return (self.product_id.barcode, '010', 'GTIN')
            elif self.product_id.unspsc_code_id:
                return (self.product_id.unspsc_code_id.code, '001', 'UNSPSC')
            elif self.product_id.default_code:
                return (self.product_id.default_code, '999', 'Estándar de adopción del contribuyente')

        return ('1010101', '001', '')

    def _l10n_co_edi_get_iae3_value(self, product_code):
        value = {
            '010': '9',
            '001': '10',
        }
        return value.get(product_code, '')

    def _l10n_co_edi_get_line_name(self):
        """
        Ensure the text we use for electronic communications follows
        Carvajal specifications
        """
        self.ensure_one()
        return textwrap.shorten(self.name or '', 300)
