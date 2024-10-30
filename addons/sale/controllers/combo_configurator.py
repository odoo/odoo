# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.http import Controller, request, route
from odoo.tools import groupby


class SaleComboConfiguratorController(Controller):

    @route(route='/sale/combo_configurator/get_data', type='json', auth='user')
    def sale_combo_configurator_get_data(
        self,
        product_tmpl_id,
        quantity,
        date,
        currency_id=None,
        company_id=None,
        pricelist_id=None,
        selected_combo_items=None,
        **kwargs,
    ):
        """ Return data about the specified combo product.

        :param int product_tmpl_id: The product for which to get data, as a `product.template` id.
        :param int quantity: The quantity of the product.
        :param str date: The date to use to compute prices.
        :param int|None currency_id: The currency to use to compute prices, as a `res.currency` id.
        :param int|None company_id: The company to use, as a `res.company` id.
        :param int|None pricelist_id: The pricelist to use to compute prices, as a
            `product.pricelist` id.
        :param list(dict) selected_combo_items: The selected combo items, in the following format:
            {
                'id': int,
                'no_variant_ptav_ids': list(int),
                'custom_ptavs': list({
                    'id': int,
                    'value': str,
                }),
            }
        :param dict kwargs: Locally unused data passed to `_get_configurator_display_price` and
            `_get_additional_configurator_data`.
        :rtype: dict
        :return: A dict containing data about the combo product.
        """
        if company_id:
            request.update_context(allowed_company_ids=[company_id])
        product_template = request.env['product.template'].browse(product_tmpl_id)
        currency = request.env['res.currency'].browse(currency_id)
        pricelist = request.env['product.pricelist'].browse(pricelist_id)
        date = datetime.fromisoformat(date)
        selected_combo_item_dict = {item['id']: item for item in selected_combo_items or []}

        return {
            'product_tmpl_id': product_tmpl_id,
            'display_name': product_template.display_name,
            'quantity': quantity,
            'price': product_template._get_configurator_display_price(
                product_template, quantity, date, currency, pricelist, **kwargs
            ),
            'combos': [{
                'id': combo.id,
                'name': combo.name,
                'combo_items': [
                   self. _get_combo_item_data(
                       combo,
                       combo_item,
                       selected_combo_item_dict.get(combo_item.id, {}),
                       date,
                       currency,
                       pricelist,
                       **kwargs,
                   ) for combo_item in combo.combo_item_ids
                ],
            } for combo in product_template.combo_ids.sudo()],
            'currency_id': currency_id,
            **product_template._get_additional_configurator_data(
                product_template, date, currency, pricelist, **kwargs
            ),
        }

    @route(route='/sale/combo_configurator/get_price', type='json', auth='user')
    def sale_combo_configurator_get_price(
        self,
        product_tmpl_id,
        quantity,
        date,
        currency_id=None,
        company_id=None,
        pricelist_id=None,
        **kwargs,
    ):
        """ Return the price of the specified combo product.

        :param int product_tmpl_id: The product for which to get the price, as a `product.template`
            id.
        :param int quantity: The quantity of the product.
        :param str date: The date to use to compute the price.
        :param int|None currency_id: The currency to use to compute the price, as a `res.currency`
            id.
        :param int|None company_id: The company to use, as a `res.company` id.
        :param int|None pricelist_id: The pricelist to use to compute the price, as a
            `product.pricelist` id.
        :param dict kwargs: Locally unused data passed to `_get_configurator_display_price`.
        :rtype: float
        :return: The price of the combo product.
        """
        if company_id:
            request.update_context(allowed_company_ids=[company_id])
        product_template = request.env['product.template'].browse(product_tmpl_id)
        currency = request.env['res.currency'].browse(currency_id)
        pricelist = request.env['product.pricelist'].browse(pricelist_id)
        date = datetime.fromisoformat(date)

        return product_template._get_configurator_display_price(
            product_template, quantity, date, currency, pricelist, **kwargs
        )

    def _get_combo_item_data(
        self, combo, combo_item, selected_combo_item, date, currency, pricelist, **kwargs
    ):
        """ Return the price of the specified combo product.

        :param product.combo combo: The combo for which to get the data.
        :param product.combo.item combo_item: The combo for which to get the data.
        :param datetime date: The date to use to compute prices.
        :param product.pricelist pricelist: The pricelist to use to compute prices.
        :param dict kwargs: Locally unused data passed to `_get_additional_configurator_data`.
        :rtype: dict
        :return: A dict containing data about the combo item.
        """
        ptals_data = self._get_ptals_data(combo_item.product_id, selected_combo_item)
        # If the combo choice has only one combo item, and that combo item can't be configured (i.e.
        # it has no `no_variant` attributes), then it should be preselected, as the user has to
        # select it anyway.
        is_preselected = len(combo.combo_item_ids) == 1 and not any(
            ptal['create_variant'] == 'no_variant' for ptal in ptals_data
        )

        return {
            'id': combo_item.id,
            'extra_price': combo_item.extra_price,
            'is_selected': bool(selected_combo_item),
            'is_preselected': is_preselected,
            'product': {
                'id': combo_item.product_id.id,
                'product_tmpl_id': combo_item.product_id.product_tmpl_id.id,
                'display_name': combo_item.product_id.display_name,
                'ptals': ptals_data,
                **request.env['product.template']._get_additional_configurator_data(
                    combo_item.product_id, date, currency, pricelist, **kwargs
                ),
            },
        }

    def _get_ptals_data(self, product, selected_combo_item):
        """ Return data about the PTALs of the specified product.

        :param product.product product: The product for which to get the PTALs.
        :param dict selected_combo_item: The selected combo item, in the following format:
            {
                'id': int,
                'no_variant_ptav_ids': list(int),
                'custom_ptavs': list({
                    'id': int,
                    'value': str,
                }),
            }
        :rtype: list(dict)
        :return: A list of dicts containing data about the specified product's PTALs.
        """
        variant_ptavs = product.product_template_attribute_value_ids
        no_variant_ptavs = request.env['product.template.attribute.value'].browse(
            selected_combo_item.get('no_variant_ptav_ids')
        )
        ptavs_by_ptal_id = dict(groupby(
            variant_ptavs + no_variant_ptavs, lambda ptav: ptav.attribute_line_id.id
        ))

        custom_ptavs = selected_combo_item.get('custom_ptavs', [])
        custom_value_by_ptav_id = {ptav['id']: ptav['value'] for ptav in custom_ptavs}

        return [{
            'id': ptal.id,
            'name': ptal.attribute_id.name,
            'create_variant': ptal.attribute_id.create_variant,
            'selected_ptavs': self._get_selected_ptavs_data(
                ptavs_by_ptal_id.get(ptal.id, []), custom_value_by_ptav_id
            ),
        } for ptal in product.attribute_line_ids]

    def _get_selected_ptavs_data(self, selected_ptavs, custom_value_by_ptav_id):
        """ Return data about the selected PTAVs of the specified product.

        :param list(product.template.attribute.value) selected_ptavs: The selected PTAVs.
        :param dict custom_value_by_ptav_id: A mapping from PTAV ids to custom values.
        :rtype: list(dict)
        :return: A list of dicts containing data about the specified PTAL's selected PTAVs.
        """
        return [{
            'id': ptav.id,
            'name': ptav.name,
            'price_extra': ptav.price_extra,
            'custom_value': custom_value_by_ptav_id.get(ptav.id),
        } for ptav in selected_ptavs]
