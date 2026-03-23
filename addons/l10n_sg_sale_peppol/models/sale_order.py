from odoo import api, fields, models
from odoo.exceptions import UserError
from base64 import b64encode


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    l10n_sg_peppol_message_uuid = fields.Char(string='PEPPOL message ID')
    l10n_sg_peppol_order_id = fields.Char(string="PEPPOL order document ID")
    l10n_sg_peppol_order_tx_ids = fields.One2many(
        'sale.peppol.advanced.order.transaction',
        'order_id',
        string="EDI Trackers",
    )

    l10n_sg_has_pending_order = fields.Boolean(compute='_has_pending_order')
    l10n_sg_has_pending_order_change = fields.Boolean(compute='_has_pending_order_change')
    l10n_sg_has_pending_order_cancel = fields.Boolean(compute='_has_pending_order_cancel')

    @api.model
    def _peppol_create_order_from_attachment(self, attachments):
        """Create sale order(s) from PEPPOL attachment(s) using the PEPPOL-specific decoder
        (no price_unit recomputation). Bypasses _get_edi_decoder by pre-setting decoder_info,
        so manual file import continues to use the standard decoder with price recompute.
        """
        grouping_method = self._group_files_data_by_origin_attachment
        files_data = self._to_files_data(attachments)
        files_data.extend(self._unwrap_attachments(files_data))
        file_data_groups = grouping_method(files_data)

        records = self.create([{}] * len(file_data_groups))
        peppol_decoder_info = {
            'priority': 30,
            'decoder': self.env['sale.edi.xml.ubl_bis3_advanced_order']._peppol_import_order_ubl,
        }
        for record, file_data_group in zip(records, file_data_groups):
            for file_data in file_data_group:
                file_data['decoder_info'] = peppol_decoder_info
            attachment_records = self._from_files_data(file_data_group)
            attachment_records.write({
                'res_model': record._name,
                'res_id': record.id,
            })
            record.message_post(
                body=self.env._("This document was created from the following attachment(s)."),
                attachment_ids=attachment_records.ids,
            )

        for record, file_data_group in zip(records, file_data_groups):
            record._extend_with_attachments(file_data_group, new=True)

        return records

    def action_accept_peppol_order(self):
        order_tx = self.l10n_sg_peppol_order_tx_ids.filtered_domain([
            ('document_type', '=', 'order'),
        ]).sorted()[:1]
        if not order_tx:
            raise UserError(self.env._("There is no related advanced order transaction."))

        self._send_order_response_advanced(order_tx, "AP")
        order_tx.state = 'accepted'

        if self.state in ('draft', 'sent'):
            self.action_confirm()

        self.message_post(
            body=self.env._("The order document has been accepted."),
        )

    def action_reject_peppol_order(self):
        order_tx = self.l10n_sg_peppol_order_tx_ids.filtered_domain([
            ('document_type', '=', 'order'),
        ]).sorted()[:1]
        if not order_tx:
            raise UserError(self.env._("There is no related advanced order transaction."))

        self._send_order_response_advanced(order_tx, "RE")
        order_tx.state = 'rejected'

        self.message_post(
            body=self.env._("The order document has been rejected."),
        )

    def action_apply_peppol_order_change(self):
        order_change_tx = self.l10n_sg_peppol_order_tx_ids.filtered_domain([
            ('document_type', '=', 'order_change'),
        ]).sorted()[:1]
        if not order_change_tx:
            raise UserError(self.env._("There is no pending order change request for this order."))

        attachment = order_change_tx.attachment_id
        self.env['sale.edi.xml.ubl_bis3_order_change'].process_peppol_order_change(self, attachment)

        self._send_order_response_advanced(order_change_tx, "AP")
        order_change_tx.state = 'accepted'

    def action_reject_peppol_order_change(self):
        order_change_tx = self.l10n_sg_peppol_order_tx_ids.filtered_domain([
            ('document_type', '=', 'order_change'),
        ]).sorted()[:1]
        if not order_change_tx:
            raise UserError(self.env._("There is no pending order change request for this order."))

        self._send_order_response_advanced(order_change_tx, "RE")
        order_change_tx.state = 'rejected'

    def action_apply_peppol_order_cancel(self):
        for order in self:
            order_cancel_tx = order.l10n_sg_peppol_order_tx_ids.filtered_domain([
                ('document_type', '=', 'order_cancel'),
                ('state', '=', 'to_reply'),
            ]).sorted()[:1]
            if not order_cancel_tx:
                raise UserError(order.env._("There is no pending order cancellation request for this order."))

            attachment = order_cancel_tx.attachment_id
            self.env['sale.edi.xml.ubl_bis3_order_cancel'].process_peppol_order_cancel(self, attachment)

            order._send_order_response_advanced(order_cancel_tx, "RE")
            order_cancel_tx.state = 'accepted'

    def action_reject_peppol_order_cancel(self):
        for order in self:
            order_cancel_tx = order.l10n_sg_peppol_order_tx_ids.filtered_domain([
                ('document_type', '=', 'order_cancel'),
                ('state', '=', 'to_reply'),
            ]).sorted()[:1]
            if not order_cancel_tx:
                raise UserError(order.env._("There is no pending order cancellation request for this order."))

            order._send_order_response_advanced(order_cancel_tx, "AP")
            order_cancel_tx.state = 'rejected'

    def _send_order_response_advanced(self, order_tx, code):
        """Send an Order Response Advanced document to the buyer via PEPPOL.

        :param order_tx: PEPPOL advanced order transaction to respond to
        :param code: Response code (AP=Accepted, RE=Rejected, AB=Automatically Accepted, CA=Conditionally Accepted)
        """
        order_response_xml = self.env['sale.edi.xml.ubl_bis3_order_response_advanced'].build_order_response_xml(self, order_tx, code)
        partner = self.partner_id.commercial_partner_id.with_company(self.company_id)
        params = {
            'documents': [{
                'filename': f"{self.name}-{order_tx.document_type}-response-{order_tx.id}.xml",
                'ubl': b64encode(order_response_xml).decode(),
                'receiver': partner.routing_identifier,
            }],
        }

        edi_user = self.company_id.account_peppol_edi_user

        edi_user._call_peppol_proxy(
            "/api/peppol/1/send_document",
            params=params,
        )

    # -------------------------------------------------------------------------
    # Compute methods
    # -------------------------------------------------------------------------

    @api.depends('l10n_sg_peppol_order_tx_ids')
    def _has_pending_order(self):
        for order in self:
            order_tx = order.l10n_sg_peppol_order_tx_ids.filtered_domain([
                ('document_type', '=', 'order'),
                ('state', '=', 'to_reply'),
            ]).sorted()[:1]
            order.l10n_sg_has_pending_order = bool(order_tx)

    @api.depends('l10n_sg_peppol_order_tx_ids')
    def _has_pending_order_change(self):
        for order in self:
            order_change_tx = order.l10n_sg_peppol_order_tx_ids.filtered_domain([
                ('document_type', '=', 'order_change'),
                ('state', '=', 'to_reply'),
            ]).sorted()[:1]
            order.l10n_sg_has_pending_order_change = bool(order_change_tx)

    @api.depends('l10n_sg_peppol_order_tx_ids')
    def _has_pending_order_cancel(self):
        for order in self:
            order_cancel_tx = order.l10n_sg_peppol_order_tx_ids.filtered_domain([
                ('document_type', '=', 'order_cancel'),
                ('state', '=', 'to_reply'),
            ]).sorted()[:1]
            order.l10n_sg_has_pending_order_cancel = bool(order_cancel_tx)
