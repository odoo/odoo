# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.product.controllers.catalog import ProductCatalogController


class ProductCatalogAccountController(ProductCatalogController):

    @route('/product/catalog/get_sections', auth='user', type='jsonrpc', readonly=True)
    def product_catalog_get_sections(self, res_model, order_id, child_field, **kwargs):
        """Return the sections which are in given order to be shown in the product catalog.

        :param string res_model: The order model.
        :param int order_id: The order id.
        :param string child_field: The field name of the lines in the order model.
        :rtype: list
        :return: A list of dictionaries containing section information with following structure:
            [
                {
                    'id': int,
                    'name': string,
                    'sequence': int,
                    'line_count': int,
                },
            ]
        """
        order = request.env[res_model].browse(order_id)
        return order.with_company(order.company_id)._get_sections(child_field, **kwargs)

    @route('/product/catalog/create_section', auth='user', type='jsonrpc')
    def product_catalog_create_section(
        self, res_model, order_id, child_field, name, position, parent_id=None, **kwargs,
    ):
        """Create a new section on the given order.

        :param string res_model: The order model.
        :param int order_id: The order id.
        :param string child_field: The field name of the lines in the order model.
        :param string name: The name of the section to create.
        :param str position: The position of the section where it should be created, either 'top'
                             or 'bottom'.
        :return: A dictionary with newly created section's 'id' and 'sequence'.
        :rtype: dict
        """
        order = request.env[res_model].browse(order_id)
        return order.with_company(order.company_id)._create_section(
            child_field, name, position, parent_id, **kwargs,
        )

    @route('/product/catalog/resequence_sections', auth='user', type='jsonrpc')
    def product_catalog_resequence_sections(
        self, res_model, order_id, child_field, id, parent_id, before_id=None, **kwargs,
    ):
        """Reorder the sections of a given order.

        param string res_model: The order model.
        :param int order_id: The order id.
        :param list sections:  A list of section dictionaries with their sequence.
        :param string child_field: The field name of the lines in the order model.
        :return: A dictionary with new sequences of the sections.
        :rtype: dict
        """
        order = request.env[res_model].browse(order_id)
        return order.with_company(order.company_id)._resequence_sections(
            child_field, id, parent_id, before_id, **kwargs,
        )

    @route('/product/catalog/delete_section', auth='user', type='jsonrpc')
    def product_catalog_delete_section(self, res_model, order_id, child_field, section_id, **kwargs):
        """Delete the given section.

        :param int section_id: The section id.
        """
        order = request.env[res_model].browse(order_id)
        return order.with_company(order.company_id)._delete_section(child_field, section_id, **kwargs)

    @route('/product/catalog/duplicate_section', auth='user', type='jsonrpc')
    def product_catalog_duplicate_section(self, res_model, order_id, child_field, section_id, parent_id=None, **kwargs):
        """Duplicate the given section.

        :param int section_id: The section id.
        :return: A dictionary with duplicated section's 'id' and 'sequence'.
        :rtype: dict
        """
        order = request.env[res_model].browse(order_id)
        return order.with_company(order.company_id)._duplicate_section(child_field, section_id, parent_id, **kwargs)

    @route('/product/catalog/toggle_field_of_section', auth='user', type='jsonrpc')
    def product_catalog_toggle_field_of_section(self, res_model, order_id, child_field, section_id, field, **kwargs):
        """Toggle the collapse state of the given section.

        :param int section_id: The section id.
        :return: A dictionary with the updated section's 'id' and 'collapse_prices' status.
        :rtype: dict
        """
        order = request.env[res_model].browse(order_id)
        return order.with_company(order.company_id)._toggle_field_of_section(child_field, section_id, field, **kwargs)
