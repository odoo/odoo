from odoo import api, fields, models
from odoo.addons.l10n_es_edi_tbai.models.account_move import TBAI_REFUND_REASONS

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
    l10n_es_tbai_post_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string='TicketBAI Post Attachment',
        related='l10n_es_tbai_post_document_id.xml_attachment_id'
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
        for move in self:
            state = 'to_send'
            if move.l10n_es_tbai_post_document_id and move.l10n_es_tbai_post_document_id.state == 'accepted':
                state = 'sent'

            move.l10n_es_tbai_state = state

    # -------------------------------------------------------------------------
    # OVERRIDES
    # -------------------------------------------------------------------------

    def action_pos_order_invoice(self):
        if self.l10n_es_tbai_is_required and self.refunded_order_id and not self.refunded_order_id.account_move:
            raise UserError(_("You cannot invoice a refund whose related order hasn't been invoiced yet."))

        return super().action_pos_order_invoice()

    def action_pos_order_paid(self):
        res = super().action_pos_order_paid

        if not self.to_invoice and self.l10n_es_tbai_is_required:
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

        if self.l10n_es_tbai_is_required:
            return (self.account_move or self).l10n_es_tbai_post_document_id._get_tbai_qr()

    # -------------------------------------------------------------------------
    # WEB SERVICE CALL
    # -------------------------------------------------------------------------

    def _l10n_es_tbai_create_edi_document(self, cancel=False):
        return self.sudo().env['l10n_es_edi_tbai.document'].create({
            'name': self.name,
            'company_id': self.company_id.id,
            'is_cancel': False,
            'date': fields.Date.today(),
        })

    def _l10n_es_tbai_post(self):
        self.ensure_one()

        if self.l10n_es_tbai_post_document_id and self.l10n_es_tbai_post_document_id.state == 'rejected':
            self.l10n_es_tbai_post_document_id.sudo().unlink()

        edi_document = self.l10n_es_tbai_post_document_id

        if not edi_document:
            edi_document = self.l10n_es_tbai_post_document_id = self._l10n_es_tbai_create_edi_document()

        xml_values = self._l10n_es_tbai_get_values()
        error = edi_document._post_to_web_service(xml_values)
        if error:
            return error

        if edi_document.state == 'accepted':
            self.l10n_es_tbai_state = 'sent'
            return

        # Return the error message if the xml document was not accepted
        return edi_document.response_message

    # -------------------------------------------------------------------------
    # XML VALUES
    # -------------------------------------------------------------------------

    def _l10n_es_tbai_get_values(self):
        self.ensure_one()

        return {
            'is_sale': True,
            'partner': self.partner_id,
            'is_simplified': True,
            'invoice_date': self.date_order,
            **self._l10n_es_tbai_get_attachment_values(),
            **self._l10n_es_tbai_get_credit_note_values(),
            **self._l10n_es_tbai_get_tax_details(),
            'invoice_origin': False,
            'taxes': self.lines.tax_ids,
            'rate': self.currency_rate,
            'base_lines': [line._convert_to_tax_base_line_dict() for line in self.lines],
        }

    def _l10n_es_tbai_get_attachment_values(self):
        return {
            'attachment_name': self.name + '_post.xml',
            'res_model': 'pos.order',
            'res_id': self.id,
        }

    def _l10n_es_tbai_get_credit_note_values(self):
        return {
            'is_refund': self.amount_total < 0,
            'credit_note_code': 'R5',
            'credit_note_doc': self.refunded_order_id.l10n_es_tbai_post_document_id,
            'credit_note_invoice_date': self.refunded_order_id.date_order if self.refunded_order_id else False,
        }

    def _l10n_es_tbai_get_tax_details(self):
        if not self.partner_id or not self.partner_id._l10n_es_is_foreign():
            return {'tax_details_info_vals': self._l10n_es_tbai_get_order_tax_details_info()}
        else:
            return {
                'tax_details_info_service_vals': self._l10n_es_tbai_get_order_tax_details_info(
                    filter_invl_to_apply=lambda x: any(t.tax_scope == 'service' for t in x.tax_ids)
                ),
                'tax_details_info_consu_vals': self._l10n_es_tbai_get_order_tax_details_info(
                    filter_invl_to_apply=lambda x: any(t.tax_scope == 'consu' for t in x.tax_ids)
                ),
            }

    def _l10n_es_tbai_get_order_tax_details_info(self, filter_invl_to_apply=None):

        def grouping_key_generator(base_line, tax_values):
            tax = tax_values['tax_repartition_line'].tax_id
            return {
                'applied_tax_amount': tax.amount,
                'l10n_es_type': tax.l10n_es_type,
                'l10n_es_exempt_reason': tax.l10n_es_exempt_reason if tax.l10n_es_type == 'exento' else False,
                'l10n_es_bien_inversion': tax.l10n_es_bien_inversion,
            }

        def filter_to_apply(base_line, tax_values):
            # For intra-community, we do not take into account the negative repartition line
            return (tax_values['tax_repartition_line'].factor_percent > 0.0
                    and tax_values['tax_repartition_line'].tax_id.amount != -100.0
                    and tax_values['tax_repartition_line'].tax_id.l10n_es_type != 'ignore')

        def full_filter_invl_to_apply(invoice_line):
            if all(t == 'ignore' for t in invoice_line.tax_ids.flatten_taxes_hierarchy().mapped('l10n_es_type')):
                return False
            return filter_invl_to_apply(invoice_line) if filter_invl_to_apply else True

        tax_details = self._prepare_order_aggregated_taxes(
            grouping_key_generator=grouping_key_generator,
            filter_invl_to_apply=full_filter_invl_to_apply,
            filter_tax_values_to_apply=filter_to_apply,
        )

        # Detect for which is the main tax for 'recargo'. Since only a single combination tax + recargo is allowed
        # on the same invoice, this can be deduced globally.

        recargo_tax_details = {}  # Mapping between main tax and recargo tax details
        order_lines = self.lines
        if filter_invl_to_apply:
            order_lines = order_lines.filtered(filter_invl_to_apply)
        for line in order_lines:
            taxes = line.tax_ids.flatten_taxes_hierarchy()
            recargo_tax = [t for t in taxes if t.l10n_es_type == 'recargo']
            if recargo_tax and taxes:
                recargo_main_tax = taxes.filtered(lambda x: x.l10n_es_type in ('sujeto', 'sujeto_isp'))[:1]
                if not recargo_tax_details.get(recargo_main_tax):
                    recargo_tax_details[recargo_main_tax] = next(
                        x for x in tax_details['tax_details'].values()
                        if x['group_tax_details'][0]['tax_repartition_line'].tax_id == recargo_tax[0]
                    )

        sign = -1 if self.amount_total < 0 else 1

        return {
            **self.env['account.move']._l10n_es_edi_get_tax_details_info(tax_details, recargo_tax_details, sign, True, self.company_id),
            'tax_details': tax_details,
        }

    def _prepare_order_aggregated_taxes(self, filter_invl_to_apply=None, filter_tax_values_to_apply=None, grouping_key_generator=None, distribute_total_on_line=True):
        self.ensure_one()
        company = self.company_id

        # Prepare the tax details for each line.
        to_process = []
        for order_line in self.lines:
            base_line = order_line._convert_to_tax_base_line_dict()
            tax_details_results = self.env['account.tax']._prepare_base_line_tax_details(base_line, company)
            to_process.append((base_line, tax_details_results))

        return self.env['account.tax']._aggregate_taxes(
            to_process,
            company,
            filter_tax_values_to_apply=filter_tax_values_to_apply,
            grouping_key_generator=grouping_key_generator,
            distribute_total_on_line=distribute_total_on_line,
        )
