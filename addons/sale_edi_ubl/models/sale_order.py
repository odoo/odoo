from odoo import _, api, models, Command


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def _get_record_ubl_builder_from_xml_tree(self, tree):
        """ Return sale order ubl builder with decording capibily to given tree

        :param xml tree: xml tree to find builder.
        :return class: class object of builder for given tree if found else none.
        """
        customization_id = tree.find('{*}CustomizationID')
        if customization_id is not None:
            if customization_id.text == 'urn:fdc:peppol.eu:poacc:trns:order:3':
                return self.env['sale.edi.xml.ubl_bis3']

    def _create_activity_set_details(self):
        """ Create activity on sale order to set details.

        :return: None.
        """
        activity_message = _("Some information could not be imported")
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=self.env.user.id,
            note=activity_message,
        )

    @api.model
    def _get_line_vals_list(self, lines_vals):
        """ Get sale order line values list.

        :param list line_vals: List of values [name, qty, price, tax].
        :return: List of dict values.
        """

        return [{
            'sequence': 0,  # be sure to put these lines above the 'real' order lines
            'name': name,
            'product_uom_qty': quantity,
            'price_unit': price_unit,
            'tax_ids': [Command.set(tax_ids)],
        } for name, quantity, price_unit, tax_ids in lines_vals]

    def _get_supplier_id(self):
        return self.company_id.partner_id

    def _get_edi_builders(self):
        return super()._get_edi_builders() + [self.env['sale.edi.xml.ubl_bis3']]
