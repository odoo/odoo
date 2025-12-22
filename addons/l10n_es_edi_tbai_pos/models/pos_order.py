from odoo import api, fields, models
from odoo.addons.l10n_es_edi_tbai.models.account_move import TBAI_REFUND_REASONS
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_es_tbai_state = fields.Selection([
            ('to_send', 'To Send'),
            ('sent', 'Sent'),
        ],
        string='TicketBAI status',
        compute='_compute_l10n_es_tbai_state',
    )
    l10n_es_tbai_chain_index = fields.Integer(
        string="TicketBAI chain index",
        help="Invoice index in chain, set if and only if an in-chain XML was submitted and did not error",
        related='l10n_es_tbai_post_document_id.chain_index',
    )

    l10n_es_tbai_post_document_id = fields.Many2one(
        comodel_name='l10n_es_edi_tbai.document',
        copy=False,
    )

    l10n_es_tbai_post_file = fields.Binary(
        string="TicketBAI Post File",
        related='l10n_es_tbai_post_document_id.xml_attachment_id.datas',
    )
    l10n_es_tbai_post_file_name = fields.Char(
        string="TicketBAI Post Attachment Name",
        related="l10n_es_tbai_post_document_id.xml_attachment_id.name",
    )

    l10n_es_tbai_is_required = fields.Boolean(
        string="TicketBAI required",
        related="company_id.l10n_es_tbai_is_enabled",
    )

    l10n_es_tbai_refund_reason = fields.Selection(
        selection=TBAI_REFUND_REASONS,
        string="Invoice Refund Reason Code (TicketBai)",
        help="BOE-A-1992-28740. Ley 37/1992, de 28 de diciembre, del Impuesto sobre el "
        "Valor Añadido. Artículo 80. Modificación de la base imponible.",
        copy=False,
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('l10n_es_tbai_post_document_id.state')
    def _compute_l10n_es_tbai_state(self):
        for order in self:
            state = 'to_send' if order.l10n_es_tbai_is_required and not order.account_move else None
            if order.l10n_es_tbai_post_document_id and order.l10n_es_tbai_post_document_id.state == 'accepted':
                state = 'sent'

            order.l10n_es_tbai_state = state

    # -------------------------------------------------------------------------
    # OVERRIDES
    # -------------------------------------------------------------------------

    def _process_saved_order(self, draft):
        if not self.l10n_es_tbai_is_required:
            return super()._process_saved_order(draft)

        self.ensure_one()

        if not self.to_invoice and self.amount_total > self.company_id.l10n_es_simplified_invoice_limit:
            raise UserError(self.env._("Please create an invoice for an amount over %s.", self.company_id.l10n_es_simplified_invoice_limit))

        if self.refunded_order_id:
            if self.to_invoice and self.refunded_order_id.state != 'invoiced':
                raise UserError(self.env._("You cannot invoice a refund whose linked order hasn't been invoiced."))
            if not self.to_invoice and self.refunded_order_id.state == 'invoiced':
                raise UserError(self.env._("Please invoice the refund as the linked order has been invoiced."))

        return super()._process_saved_order(draft)

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid()

        if self.l10n_es_tbai_is_required and not self.to_invoice:
            error = self._l10n_es_tbai_post()

            if error:
                chain_head_doc = self.company_id._get_l10n_es_tbai_last_chained_document()
                chain_head_order = self.search([('l10n_es_tbai_post_document_id', '=', chain_head_doc.id)])

                if chain_head_doc and chain_head_order and chain_head_order != self and chain_head_doc.state != 'accepted':
                    chain_head_order._l10n_es_tbai_post()
                    if self.env['account.move.send']._can_commit():
                        self.env.cr.commit()
                    self._l10n_es_tbai_post()

        return res

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()

        if self.l10n_es_tbai_is_required:
            vals['l10n_es_tbai_refund_reason'] = self.l10n_es_tbai_refund_reason

        return vals

    # -------------------------------------------------------------------------
    # PUBLIC METHODS
    # -------------------------------------------------------------------------

    def get_l10n_es_pos_tbai_qrurl(self):
        """ Retrieve the QR Code from the related ticketbai document . """
        self.ensure_one()

        edi_document = self.account_move.l10n_es_tbai_post_document_id or self.l10n_es_tbai_post_document_id
        if edi_document and edi_document.state == 'accepted':
            return edi_document._get_tbai_qr()
        return ''

    # -------------------------------------------------------------------------
    # WEB SERVICE CALL
    # -------------------------------------------------------------------------

    def l10n_es_tbai_retry_post(self):
        error = self._l10n_es_tbai_post()
        if error:
            raise UserError(error)

    def _l10n_es_tbai_post(self):
        self.ensure_one()

        if self.l10n_es_tbai_post_document_id and self.l10n_es_tbai_post_document_id.state == 'rejected':
            self.l10n_es_tbai_post_document_id.sudo().unlink()

        if not self.l10n_es_tbai_post_document_id:
            self.l10n_es_tbai_post_document_id = self._l10n_es_tbai_create_edi_document()

        edi_document = self.l10n_es_tbai_post_document_id

        error = edi_document._post_to_web_service(self._l10n_es_tbai_get_values())
        if error:
            return error

        if edi_document.state == 'accepted':
            return

        # Return the error message if the xml document was not accepted
        return edi_document.response_message

    def _l10n_es_tbai_create_edi_document(self, cancel=False):
        return self.sudo().env['l10n_es_edi_tbai.document'].create({
            'name': self.name,
            'company_id': self.company_id.id,
            'is_cancel': False,
            'date': self.date_order,
        })

    # -------------------------------------------------------------------------
    # XML VALUES
    # -------------------------------------------------------------------------

    def _l10n_es_tbai_get_values(self):
        self.ensure_one()

        base_lines = self.lines._prepare_tax_base_line_values()
        for base_line in base_lines:
            base_line['name'] = base_line['record'].name
        self.env['l10n_es_edi_tbai.document']._add_base_lines_tax_amounts(base_lines, self.company_id)

        for base_line in base_lines:
            sign = base_line['is_refund'] and -1 or 1
            base_line['gross_price_unit'] = sign * base_line['gross_price_unit']
            base_line['discount_amount'] = sign * base_line['discount_amount']
            base_line['price_total'] = sign * base_line['price_total']

        return {
            'is_sale': True,
            'partner': self.partner_id,
            'is_simplified': True,
            'delivery_date': None,
            **self._l10n_es_tbai_get_attachment_values(),
            **self._l10n_es_tbai_get_credit_note_values(),
            'origin': 'manual',
            'taxes': self.lines.tax_ids,
            'rate': self.currency_rate,
            'base_lines': base_lines,
        }

    def _l10n_es_tbai_get_attachment_values(self):
        return {
            'attachment_name': self.name + '_post.xml',
            'res_model': 'pos.order',
            'res_id': self.id,
        }

    def _l10n_es_tbai_get_credit_note_values(self):
        return {
            'is_refund': bool(self.refunded_order_id),
            'refund_reason': 'R5',
            'refunded_doc': self.refunded_order_id.l10n_es_tbai_post_document_id,
            'refunded_doc_invoice_date': self.refunded_order_id.date_order if self.refunded_order_id else False,
            'refunded_name': self.refunded_order_id.name,
        }
