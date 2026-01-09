from odoo import api, fields, models
from odoo.exceptions import UserError
from base64 import b64encode


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    peppol_message_uuid = fields.Char(string='PEPPOL message ID')
    peppol_order_state = fields.Selection(
        selection=[
            ('ready', 'Ready to send'),
            ('to_send', 'Queued'),
            ('skipped', 'Skipped'),
            ('processing', 'Pending Reception'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        store=True,
        string='PEPPOL status',
        copy=False,
    )
    peppol_order_id = fields.Char(string="PEPPOL order document ID")
    peppol_order_change_id = fields.Char(string="PEPPOL order change document ID")
    peppol_order_transaction_ids = fields.One2many(
        'sale.peppol.advanced.order.tracker',
        'order_id',
        string="EDI Trackers",
    )

    l10n_sg_has_pending_order = fields.Boolean(compute='_has_pending_order')
    l10n_sg_has_pending_order_change = fields.Boolean(compute='_has_pending_order_change')
    l10n_sg_has_pending_order_cancel = fields.Boolean(compute='_has_pending_order_cancel')

    def action_confirm(self):
        super().action_confirm()
        self.env['sale.edi.xml.ubl_bis3_order_response_advanced'].build_order_response_xml(self, 'AP')
        # Send this via peppol

    # =================== #
    # === EDI Decoder === #
    # =================== #
    def _get_edi_builders(self):
        return super()._get_edi_builders() + [self.env['sale.edi.xml.ubl_bis3_advanced_order']]

    def _get_import_file_type(self, file_data):
        """ OVERRIDE `sale_edi_ubl` module to identify UBL files.
        """
        if (tree := file_data['xml_tree']) is not None:
            profile_id = tree.find('{*}ProfileID')
            if profile_id is not None:
                if profile_id.text == 'urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3':
                    return 'sale.edi.xml.ubl_bis3_advanced_order'
        return super()._get_import_file_type(file_data)

    def _get_edi_decoder(self, file_data, new=False):
        """ Override of sale to add edi decoder for xml files.

        :param dict file_data: File data to decode.
        """
        if file_data['import_file_type'] == 'sale.edi.xml.ubl_bis3_advanced_order':
            return {
                'priority': 30,
                'decoder': self.env['sale.edi.xml.ubl_bis3_advanced_order']._import_order_ubl,
            }
        return super()._get_edi_decoder(file_data, new)

    def action_accept_peppol_order(self):
        order_tx = self.peppol_order_transaction_ids.filtered_domain([
            ('document_type', '=', 'order'),
        ]).sorted()[:1]
        if not order_tx:
            raise UserError(self.env._("There is no related advanced order transaction."))

        self._send_order_response_advanced(order_tx, "AP")
        order_tx.state = 'accepted'

    def action_reject_peppol_order(self):
        order_tx = self.peppol_order_transaction_ids.filtered_domain([
            ('document_type', '=', 'order'),
        ]).sorted()[:1]
        if not order_tx:
            raise UserError(self.env._("There is no related advanced order transaction."))

        self._send_order_response_advanced(order_tx, "RE")
        order_tx.state = 'rejected'

    def action_apply_peppol_order_change(self):
        order_change_tx = self.peppol_order_transaction_ids.filtered_domain([
            ('document_type', '=', 'order_change'),
        ]).sorted()[:1]
        if not order_change_tx:
            raise UserError(self.env._("There is no pending order change request for this order."))

        attachment = order_change_tx.attachment_id
        self.env['sale.edi.xml.ubl_bis3_order_change'].process_peppol_order_change(self, attachment)

        self._send_order_response_advanced(order_change_tx, "AP")
        order_change_tx.state = 'accepted'

    def action_reject_peppol_order_change(self):
        order_change_tx = self.peppol_order_transaction_ids.filtered_domain([
            ('document_type', '=', 'order_change'),
        ]).sorted()[:1]
        if not order_change_tx:
            raise UserError(self.env._("There is no pending order change request for this order."))

        self._send_order_response_advanced(order_change_tx, "RE")
        order_change_tx.state = 'rejected'

    def action_apply_peppol_order_cancel(self):
        for order in self:
            order_cancel_tx = order.peppol_order_transaction_ids.filtered_domain([
                ('document_type', '=', 'order_cancel'),
            ]).sorted()[:1]
            if not order_cancel_tx:
                raise UserError(order.env._("There is no pending order change request for this order."))

            attachment = order_cancel_tx.attachment_id
            self.env['sale.edi.xml.ubl_bis3_order_cancel'].process_peppol_order_cancel(self, attachment)

            order._send_order_response_advanced(order_cancel_tx, "RE")
            order_cancel_tx.state = 'accepted'

    def action_reject_peppol_order_cancel(self):
        for order in self:
            order_cancel_tx = order.peppol_order_transaction_ids.filtered_domain([
                ('document_type', '=', 'order_cancel'),
            ]).sorted()[:1]
            if not order_cancel_tx:
                raise UserError(order.env._("There is no pending order change request for this order."))

            order._send_order_response_advanced(order_cancel_tx, "AP")
            order_cancel_tx.state = 'rejected'

    def _send_order_response_advanced(self, peppol_advanced_order_tx, code):
        """
        Docstring for _send_order_response_advanced

        :param peppol_advanced_order_tx: PEPPOL advanced order transaction to respond to
        :param code: Response code (AP or RE)
        """
        attachment = peppol_advanced_order_tx.attachment_id
        order_response_xml = self.env['sale.edi.xml.ubl_bis3_order_response_advanced'].build_order_response_xml(self, code)
        partner = self.partner_id.commercial_partner_id.with_company(self.company_id)
        params = {
            'documents': [{
                'filename': f"{attachment.name}-response-{code}",
                'ubl': b64encode(order_response_xml).decode(),
                'receiver': f"{partner.peppol_eas}:{partner.peppol_endpoint}",
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

    @api.depends('peppol_order_transaction_ids')
    def _has_pending_order(self):
        for order in self:
            order_tx = order.peppol_order_transaction_ids.filtered_domain([
                ('document_type', '=', 'order'),
                ('state', '=', 'to_reply'),
            ]).sorted()[:1]
            order.l10n_sg_has_pending_order = bool(order_tx)

    @api.depends('peppol_order_transaction_ids')
    def _has_pending_order_change(self):
        for order in self:
            order_change_tx = order.peppol_order_transaction_ids.filtered_domain([
                ('document_type', '=', 'order_change'),
                ('state', '=', 'to_reply'),
            ]).sorted()[:1]
            order.l10n_sg_has_pending_order_change = bool(order_change_tx)

    @api.depends('peppol_order_transaction_ids')
    def _has_pending_order_cancel(self):
        for order in self:
            order_cancel_tx = order.peppol_order_transaction_ids.filtered_domain([
                ('document_type', '=', 'order_cancel'),
                ('state', '=', 'to_reply'),
            ]).sorted()[:1]
            order.l10n_sg_has_pending_order_cancel = bool(order_cancel_tx)
