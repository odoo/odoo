/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { ProductConfiguratorDialog } from "@sale_product_configurator/js/product_configurator_dialog/product_configurator_dialog";
import "@website_sale/js/website_sale";
import { getCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";

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
                    main_product: JSON.stringify(mainProduct),
                    optional_products: JSON.stringify(optionalProducts),
                    ...this._getOptionalCombinationInfoParam(),
                });
                if (goToShop) {
                    window.location.pathname = "/shop/cart";
                } else {
                    wSaleUtils.updateCartNavBar(values);
                    wSaleUtils.showCartNotification(callService, values.notification_info);
                }
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
     * TODO VCR
     * @param {Object} product - The product to serialize.
     * @return {Object} - The serialized product.
     */
    _serializeProduct(product) {
        // before: [{"product_id":12,"product_template_id":9,"quantity":1,"unique_id":"5","product_custom_attribute_values":[],"no_variant_attribute_values":[]}]
        // after:  [{"product_tmpl_id":9,"id":12,"description_sale":"160x80cm, with large legs.","display_name":"[FURN_0096] Customizable Desk (Steel, White)","price":750,"quantity":5,"attribute_lines":[{"id":1,"attribute":{"id":1,"name":"Legs","display_type":"radio"},"attribute_values":[{"id":1,"name":"Steel","html_color":false,"is_custom":false,"price_extra":0,"excluded":false},{"id":2,"name":"Aluminium","html_color":false,"is_custom":false,"price_extra":50.4,"excluded":false},{"id":7,"name":"Custom","html_color":false,"is_custom":true,"price_extra":0,"excluded":false}],"selected_attribute_value_ids":[1],"create_variant":"always"},{"id":2,"attribute":{"id":2,"name":"Color","display_type":"color"},"attribute_values":[{"id":3,"name":"White","html_color":"#FFFFFF","is_custom":false,"price_extra":0,"excluded":false},{"id":4,"name":"Black","html_color":"#000000","is_custom":false,"price_extra":0,"excluded":false}],"selected_attribute_value_ids":[3],"create_variant":"always"}],"exclusions":{"1":[],"2":[4],"3":[],"4":[2],"7":[]},"archived_combinations":[],"parent_exclusions":{}}]
        let serializedProduct = {  //ok
            product_id: product.id,
            product_template_id: product.product_tmpl_id,
            quantity: product.quantity,
        }

        // TODO VCR
        // handle custom values & no variants
        let customValuesCommands = [{ operation: "DELETE_ALL" }];
        for (const ptal of product.attribute_lines) {
            const selectedCustomPTAV = ptal.attribute_values.find(
                ptav => ptav.is_custom && ptav.id === ptal.selected_attribute_value_id
            );
            if (selectedCustomPTAV) customValuesCommands.push({
                operation: "CREATE",
                context: [
                    {
                        default_custom_product_template_attribute_value_id: selectedCustomPTAV.id,
                        default_custom_value: ptal.customValue,
                    },
                ],
            });
        }
        serializedProduct.product_custom_attribute_value_ids = {
            operation: "MULTI",
            commands: customValuesCommands,
        };

        let noVariantCommands = [{ operation: "DELETE_ALL" }];
        const noVariantPTAVIds = product.attribute_lines.filter(
            ptal => ptal.create_variant === "no_variant"
        ).map(ptal => { return {id: ptal.selected_attribute_value_id}});
        if (noVariantPTAVIds.length) noVariantCommands.push({
            operation: "ADD_M2M",
            ids: noVariantPTAVIds,
        });
        serializedProduct.product_no_variant_attribute_value_ids = {
            operation: "MULTI",
            commands: noVariantCommands,
        };

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
