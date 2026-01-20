from odoo import api, models


class Account_Edi_Proxy_ClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    @api.model
    def _get_proxy_urls(self):
        """Allow overriding Peppol proxy origins for local/dev setups.

        This module is often used with a locally running Peppol proxy/IAP server.
        Configure with:
          - account_peppol.proxy_origin_test = http://localhost:8649
          - account_peppol.proxy_origin_prod = http://localhost:8649   (optional)

        Values are expected to be origins (no trailing slash). If not set, fall back to
        the defaults provided by `account_peppol`.
        """
        urls = super()._get_proxy_urls()
        if 'peppol' not in urls:
            return urls

        icp = self.env['ir.config_parameter'].sudo()
        test_origin = icp.get_str('account_peppol.proxy_origin_test')
        prod_origin = icp.get_str('account_peppol.proxy_origin_prod')

        if test_origin:
            urls['peppol']['test'] = test_origin.rstrip('/')
        if prod_origin:
            urls['peppol']['prod'] = prod_origin.rstrip('/')
        return urls

    def _peppol_import_document(self, attachment, peppol_state, uuid, journal=None):
        """Import PEPPOL document as either account.move or purchase.order, depending on xml_tree's
        cbc:ProfileID element

        :param attachment: the new document
        :param peppol_state: the state of the received Peppol document
        :param uuid: the UUID of the Peppol document
        :param journal: journal to use for the new move (otherwise the company's peppol journal will be used)
        :return: the created move (if any)
        """
        self.ensure_one()

        file_data = self.env['purchase.order']._to_files_data(attachment)[0]

        customization_id = file_data['xml_tree'].findtext('.//{*}CustomizationID')
        profile_id = file_data['xml_tree'].findtext('.//{*}ProfileID')

        if (
            customization_id
            in {
                'urn:fdc:peppol.eu:poacc:trns:order_response:3',
                'urn:fdc:peppol.eu:poacc:trns:order_response_advanced:3',
            }
            and profile_id == 'urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3'
        ):
            return self._peppol_import_order_response_advanced(
                attachment, peppol_state, uuid
            )

        return super()._peppol_import_document(attachment, peppol_state, uuid, journal)

    def _peppol_import_order_response_advanced(self, attachment, peppol_state, uuid):
        """
        Import order response advanced document.

        Note: ensure_one() from account_peppol

        :param attachment: the new document
        :param peppol_state: the state of the received Peppol document
        :param uuid: the UUID of the Peppol document
        :return: UUID to ack, wrapped in dict (e.g. {'uuid': '...'})
        """
        tree = self.env['account.move']._to_files_data(attachment)[0]['xml_tree']

        order_ref_id = tree.findtext('./{*}OrderReference/{*}ID')
        order = self.env['purchase.order'].search(
            [('l10n_sg_peppol_order_id', '=', order_ref_id)]
        )
        if not order:
            return {}

        order_change_ref = tree.findtext('./{*}OrderChangeDocumentReference/{*}ID')
        order_response_code = tree.findtext('./{*}OrderResponseCode')
        order.handle_order_response_advanced(
            order_change_ref,
            order_response_code,
        )

        return {'uuid': uuid}
