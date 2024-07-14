# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields, _
from odoo.exceptions import UserError

import textwrap

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


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_co_edi_type = fields.Selection([
        ('1', 'Factura de venta'),
        ('2', 'Factura de exportación'),
        ('3', 'Documento electrónico de transmisión – tipo 03'),
        ('4', 'Factura electrónica de Venta - tipo 04'),
        ('91', 'Nota Crédito'),
        ('92', 'Nota Débito'),
        ('96', 'Eventos (Application Response)'),
    # TODO: remove 'required' in master
    ], required=True, default='1', compute='_compute_l10n_co_edi_type', store=True, string='Electronic Invoice Type')
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
                move.l10n_co_edi_type = '91'
            elif move.l10n_co_edi_debit_note:
                move.l10n_co_edi_type = '92'
            elif not move.l10n_co_edi_type:
                move.l10n_co_edi_type = '1'

    @api.depends('move_type', 'reversed_entry_id', 'edi_document_ids.state', 'l10n_co_edi_cufe_cude_ref')
    def _compute_operation_type(self):
        for rec in self:
            operation_type = False
            if rec.move_type == 'out_refund':
                if rec.reversed_entry_id:
                    operation_type = '20'
                else:
                    operation_type = '22'
            else:
                if rec.l10n_co_edi_debit_note:
                    state = rec._get_edi_document(self.env.ref('l10n_co_edi.edi_carvajal')).state
                    if state == 'sent' and not rec.l10n_co_edi_cufe_cude_ref:
                        operation_type = '23'
                    elif rec.debit_origin_id:
                        operation_type = '30'
                    else:
                        operation_type = '32'
            rec.l10n_co_edi_operation_type = operation_type or '10'

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
            if self.move_id.l10n_co_edi_type == '2':
                if not self.product_id.l10n_co_edi_customs_code:
                    raise UserError(_('Exportation invoices require custom code in all the products, please fill in this information before validating the invoice'))
                return (self.product_id.l10n_co_edi_customs_code, '020', 'Partida Alanceraria')
            if self.product_id.barcode:
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
