/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { ProductConfiguratorDialog } from "@sale_product_configurator/js/product_configurator_dialog/product_configurator_dialog";
import "@website_sale/js/website_sale";
import { _t } from "@web/core/l10n/translation";

import wSaleUtils from "@website_sale/js/website_sale_utils";

import { serializeDateTime } from "@web/core/l10n/dates";
const { DateTime } = luxon;


publicWidget.registry.WebsiteSale.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _onProductReady: function () {
        if (this.isBuyNow) {
            return this._submitForm();
        }
        this.call("dialog", "add", ProductConfiguratorDialog, {
            productTemplateId: this.rootProduct.product_template_id,
            ptavIds: this.rootProduct.variant_values,
            customAttributeValues: this.rootProduct.product_custom_attribute_values.map(
                data => {
                    return {
                        ptavId: data.custom_product_template_attribute_value_id,
                        value: data.custom_value,
                    }
                }
            ),
            quantity: this.rootProduct.quantity, //ok
            currencyId: this.rootProduct.currency_id, //ok
            soDate: serializeDateTime(DateTime.now()),
            edit: false,
            save: async (mainProduct, optionalProducts) => {
                if (optionalProducts.length) this._trackOptionalProducts(optionalProducts);

                const values = await this.rpc('/shop/cart/update_option', {
                    main_product: this._serializeProduct(mainProduct),
                    optional_products: this._serializeProduct(optionalProducts),
                });
                wSaleUtils.updateCartNavBar(values);
                wSaleUtils.showCartNotification(this.call.bind(this), values.notification_info);
                this._getCombinationInfo($.Event('click', {target: $("#add_to_cart")}));
            },
            discard: () => {},
        });
    },

    /**
     * Overridden to resolve _opened promise on modal
     * when stayOnPageOption is activated.
     *
     * @override
     */
    _submitForm() {
        var ret = this._super(...arguments);
        if (this.optionalProductsModal && this.stayOnPageOption) {
            ret.then(()=>{
                this.optionalProductsModal._openedResolver()
            });
        }
        return ret;
    },

    /**
     * Serialize the product into a format understandable by `sale.order.line`.
     * @param {Object} product - The product to serialize.
     * @return {Object} - The serialized product.
     */
    _serializeProduct(product) {
        let serializedProduct = {  //ok
            product_id: product.id,
            product_template_id: product.product_tmpl_id,
            quantity: product.quantity,
        }

        if (!product.attribute_lines) return serializedProduct;

        // handle custom values
        serializedProduct.product_custom_attribute_values = [];
        for (const ptal of product.attribute_lines) {
            const selectedCustomPTAV = ptal.attribute_values.find(
                ptav => ptav.is_custom && ptal.selected_attribute_value_ids.includes(ptav.id)
            );
            if (selectedCustomPTAV) serializedProduct.product_custom_attribute_values.push({
                custom_product_template_attribute_value_id: selectedCustomPTAV.id,
                custom_value: ptal.customValue,
            });
        }

        // handle no variants
        serializedProduct.no_variant_attribute_values = [];
        for (const ptal of product.attribute_lines) {
            if (ptal.create_variant === "no_variant" && ptal.selected_attribute_value_ids) {
                serializedProduct.no_variant_attribute_values.push(
                    ptal.selected_attribute_value_ids.map(id => {return {value: id}})
                );
            }
        }
        // TODO VCR: find a way to avoid the flat 
        serializedProduct.no_variant_attribute_values = serializedProduct.no_variant_attribute_values.flat();

        return JSON.stringify(serializedProduct);
    },

    _trackOptionalProducts: function (optionalProducts) {
        // TODO VCR: check that the main product is tracked at the opening of the modal
        const currency = this.rootProduct.currency_id; // TODO VCR the currency name is not in the session so the tracking can't be done on the name anymore
        const productsTrackingInfo = [];
        for(const product in optionalProducts) {
            productsTrackingInfo.push({
                'item_id': product.id,
                'item_name': product.display_name,
                'quantity': product.quantity,
                'currency': currency,
                'price': product.price,
            });
        }
        this.$el.trigger('add_to_cart_event', productsTrackingInfo);
    },
});

export default publicWidget.registry.WebsiteSaleOptions;
