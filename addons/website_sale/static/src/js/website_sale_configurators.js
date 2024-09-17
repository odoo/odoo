/** @odoo-module **/

import { rpc } from '@web/core/network/rpc';
import { serializeDateTime } from '@web/core/l10n/dates';
import {
    ComboConfiguratorDialog
} from '@sale/js/combo_configurator_dialog/combo_configurator_dialog';
import { ProductCombo } from "@sale/js/models/product_combo";
import {
    ProductConfiguratorDialog
} from '@sale/js/product_configurator_dialog/product_configurator_dialog';
import { serializeComboItem } from '@sale/js/sale_utils';
import { WebsiteSale } from '@website_sale/js/website_sale';
import wSaleUtils from '@website_sale/js/website_sale_utils';

const { DateTime } = luxon;

WebsiteSale.include({

    _onProductReady(isOnProductPage = false) {
        return this._openDialog(isOnProductPage);
    },

    async _openDialog(isOnProductPage) {
        const { combos, ...remainingData } = await rpc(
            '/website_sale/combo_configurator/get_data',
            {
                product_tmpl_id: this.rootProduct.product_template_id,
                quantity: this.rootProduct.quantity,
                date: serializeDateTime(DateTime.now()),
                ...this._getAdditionalRpcParams(),
            }
        );
        if (combos.length) {
            return this._openComboConfigurator(combos, remainingData);
        }
        if (this.isBuyNow) {
            return this._submitForm();
        }
        const shouldShowProductConfigurator = await rpc(
            '/website_sale/should_show_product_configurator',
            {
                product_template_id: this.rootProduct.product_template_id,
                ptav_ids: this.rootProduct.variant_values,
                is_product_configured: isOnProductPage,
            }
        );
        if (shouldShowProductConfigurator) {
            return this._openProductConfigurator(isOnProductPage);
        }
        return this._submitForm();
    },

    /**
     * Opens the product configurator dialog.
     *
     * @param isOnProductPage Whether the user is currently on the product page.
     */
    _openProductConfigurator(isOnProductPage) {
        this.call('dialog', 'add', ProductConfiguratorDialog, {
            productTemplateId: this.rootProduct.product_template_id,
            ptavIds: this.rootProduct.variant_values,
            customPtavs: this.rootProduct.product_custom_attribute_values.map(
                customPtav => ({
                    id: customPtav.custom_product_template_attribute_value_id,
                    value: customPtav.custom_value,
                })
            ),
            quantity: this.rootProduct.quantity,
            soDate: serializeDateTime(DateTime.now()),
            edit: false,
            isFrontend: true,
            options: { isMainProductConfigurable: !isOnProductPage },
            save: async (mainProduct, optionalProducts, options) => {
                this._trackProducts([mainProduct, ...optionalProducts]);

                const values = await rpc('/website_sale/product_configurator/update_cart', {
                    main_product: this._serializeProduct(mainProduct),
                    optional_products: optionalProducts.map(this._serializeProduct),
                    ...this._getAdditionalRpcParams(),
                });
                this._onConfigured(options, values);
            },
            discard: () => {},
            ...this._getAdditionalDialogProps(),
        });
    },

    /**
     * Opens the combo configurator dialog.
     *
     * @param combos The combos of the product.
     * @param remainingData Other data needed to open the combo configurator.
     */
    _openComboConfigurator(combos, remainingData) {
        this.call('dialog', 'add', ComboConfiguratorDialog, {
            combos: combos.map(combo => new ProductCombo(combo)),
            ...remainingData,
            date: serializeDateTime(DateTime.now()),
            edit: false,
            isFrontend: true,
            save: async (comboProductData, selectedComboItems, options) => {
                this._trackProducts([{
                    'id': this.rootProduct.product_id,
                    'display_name': remainingData.display_name,
                    'category_name': remainingData.category_name,
                    'currency_name': remainingData.currency_name,
                    'price': comboProductData.price,
                    'quantity': comboProductData.quantity,
                }]);

                const values = await rpc('/website_sale/combo_configurator/update_cart', {
                    combo_product_id: this.rootProduct.product_id,
                    quantity: comboProductData.quantity,
                    selected_combo_items: selectedComboItems.map(serializeComboItem),
                    ...this._getAdditionalRpcParams(),
                });
                this._onConfigured(options, values);
            },
            discard: () => {},
            ...this._getAdditionalDialogProps(),
        });
    },

    _onConfigured(options, values) {
        if (options.goToCart) {
            window.location.pathname = '/shop/cart';
        } else {
            wSaleUtils.updateCartNavBar(values);
            wSaleUtils.showCartNotification(this.call.bind(this), values.notification_info);
        }
        // Reload the product page after adding items to the cart. This is needed, for
        // example, to update the available stock.
        this._getCombinationInfo($.Event('click', { target: $('#add_to_cart') }));
    },

    /**
     * Hook to append additional props in overriding modules.
     *
     * @return {Object} The additional props.
     */
    _getAdditionalDialogProps() {
        return {};
    },

    /**
     * Hook to append additional RPC params in overriding modules.
     *
     * @return {Object} The additional RPC params.
     */
    _getAdditionalRpcParams() {
        return {};
    },

    /**
     * Serialize a product into a format understandable by the server.
     *
     * @param {Object} product The product to serialize.
     * @return {Object} The serialized product.
     */
    _serializeProduct(product) {
        let serializedProduct = {
            product_id: product.id,
            product_template_id: product.product_tmpl_id,
            parent_product_template_id: product.parent_product_tmpl_id,
            quantity: product.quantity,
        }

        if (!product.attribute_lines) {
            return serializedProduct;
        }

        // Custom attributes.
        serializedProduct.product_custom_attribute_values = [];
        for (const ptal of product.attribute_lines) {
            const selectedPtavIds = new Set(ptal.selected_attribute_value_ids);
            const selectedCustomPtav = ptal.attribute_values.find(
                ptav => ptav.is_custom && selectedPtavIds.has(ptav.id)
            );
            if (selectedCustomPtav) {
                serializedProduct.product_custom_attribute_values.push({
                    custom_product_template_attribute_value_id: selectedCustomPtav.id,
                    custom_value: ptal.customValue,
                });
            }
        }

        // No variant attributes.
        serializedProduct.no_variant_attribute_value_ids = product.attribute_lines
            .filter(ptal => ptal.create_variant === 'no_variant')
            .flatMap(ptal => ptal.selected_attribute_value_ids);

        return serializedProduct;
    },

    _trackProducts: function (products) {
        const productsTrackingInfo = []
        for (const product of products) {
            productsTrackingInfo.push({
                'item_id': product.id,
                'item_name': product.display_name,
                'item_category': product.category_name,
                'currency': product.currency_name,
                'price': product.price,
                'quantity': product.quantity,
            });
        }
        if (productsTrackingInfo.length) {
            this.$el.trigger('add_to_cart_event', productsTrackingInfo);
        }
    },
});
