from odoo import api, fields, models


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

    l10n_sg_has_peppol_order_change = fields.Boolean(default=True)
    l10n_sg_has_peppol_order_cancel = fields.Boolean(default=True)

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

    def action_apply_peppol_order_change(self):
        self.env['sale.edi.xml.ubl_bis3_order_change'].process_peppol_order_change(self)
        self.l10n_sg_has_peppol_order_change = False

    def action_reject_peppol_order_change(self):
        self.l10n_sg_has_peppol_order_cancel = False

    def action_apply_peppol_order_cancel(self):
        self.env['sale.edi.xml.ubl_bis3_order_cancel'].process_peppol_order_cancel(self)
        self.l10n_sg_has_peppol_order_cancel = False

    def action_reject_peppol_order_cancel(self):
        self.l10n_sg_has_peppol_order_cancel = False
