from odoo import _, api, models, Command


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _get_edi_builders(self):
        return super()._get_edi_builders() + [self.env['sale.edi.xml.ubl_bis3']]

    def _get_import_file_type(self, file_data):
        """ Identify UBL files. """
        # EXTENDS 'account'
        if (tree := file_data['xml_tree']) is not None:
            customization_id = tree.find('{*}CustomizationID')
            if customization_id is not None:
                if customization_id.text == 'urn:fdc:peppol.eu:poacc:trns:order:3':
                    return 'sale.edi.xml.ubl_bis3'
        return super()._get_import_file_type(file_data)

    def _get_edi_decoder(self, file_data, new=False):
        """ Override of sale to add edi decoder for xml files.

        :param dict file_data: File data to decode.
        """
        if file_data['import_file_type'] == 'sale.edi.xml.ubl_bis3':
            return {
                'priority': 20,
                'decoder': self.env['sale.edi.xml.ubl_bis3']._import_order_ubl,
            }
        return super()._get_edi_decoder(file_data, new)

    def _create_activity_set_details(self, body):
        """ Create activity on sale order to set details.

        :return: None.
        """
        activity_message = _("Some information could not be imported:")
        activity_message += body
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=self.env.user.id,
            note=activity_message,
        )

    @api.model
    def _get_line_vals_list(self, lines_vals):
        """ Get sale order line values list.

        :param list lines_vals: List of values [name, qty, price, tax].
        :return: List of dict values.
        """

        return [{
            'sequence': 0,  # be sure to put these lines above the 'real' order lines
            'name': name,
            'product_uom_qty': quantity,
            'price_unit': price_unit,
            'tax_ids': [Command.set(tax_ids)],
        } for name, quantity, price_unit, tax_ids in lines_vals]
