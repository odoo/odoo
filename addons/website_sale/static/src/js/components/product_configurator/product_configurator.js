/** @odoo-module */

import { Component, onWillStart, useState, useSubEnv } from "@odoo/owl";
import {
    ProductTemplateAttributeLine as PTAL
} from "@sale_product_configurator/js/product_template_attribute_line/product_template_attribute_line";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import wSaleUtils from '@website_sale/js/website_sale_utils';

export class ProductConfigurator extends Component {
    static components = { PTAL };
    static template = "website_sale.product_configurator.product";
    static props = {
        product_tmpl_id: Number,
        archived_combinations: Array,
        exclusions: Object,
        currency_id: Number,
        product: {
            type: Object,
            shape: {
                id: { type: [Number, {value: false}], optional: true },
                name: String,
                description_sale: [String, {value: false}], // backend sends 'false' when there is no description
                price: Number,
                quantity: Number,
                attribute_lines: Object,
            }
        },
    };

    setup() {
        this.state = useState({product: this.props.product});
        this.cartNotification = useService('cartNotificationService');

        useSubEnv({
            currencyId: this.props.currency_id,
            updateProductTemplateSelectedPTAV: this._updateProductTemplateSelectedPTAV.bind(this),
            updatePTAVCustomValue: this._updatePTAVCustomValue.bind(this),
            isPossibleCombination: this._isPossibleCombination,
        });

        onWillStart(async () => {
            this._checkExclusions(this.state.product);
        });
    }

    //--------------------------------------------------------------------------
    // Data Exchanges
    //--------------------------------------------------------------------------

    async _updateCombination(product, quantity) {
        return rpc('/website_sale/product_configurator/update_combination', {
            product_template_id: this.props.product_tmpl_id,
            combination: this._getCombination(product),
            quantity: quantity,
        });
    }


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Increase the quantity of the product in the state.
     */
    increaseQuantity() {
        this._setQuantity(this.state.product.quantity+1);
    }

    /**
     * Set the quantity of the product in the state.
     *
     * @param {Event} event
     */
    setQuantity(event) {
        this._setQuantity(parseFloat(event.target.value));
    }

    /**
     * Decrease the quantity of the product in the state.
     */
    decreaseQuantity() {
        this._setQuantity(this.state.product.quantity-1);
    }

    /**
     * Change the value of `selected_attribute_value_ids` on the given PTAL in the product.
     *
     * @param {Number} productTmplId - The product template id, as a `product.template` id.
     * @param {Number} ptalId - The PTAL id, as a `product.template.attribute.line` id.
     * @param {Number} ptavId - The PTAV id, as a `product.template.attribute.value` id.
     * @param {Boolean} multiIdsAllowed - Whether multiple `product.template.attribute.value` can be selected.
     */
    async _updateProductTemplateSelectedPTAV(productTmplId, ptalId, ptavId, multiIdsAllowed) {
        let selectedIds = this.state.product.attribute_lines.find(
            ptal => ptal.id === ptalId
        ).selected_attribute_value_ids;
        if (multiIdsAllowed) {
            const ptavID = parseInt(ptavId);
            if (!selectedIds.includes(ptavID)){
                selectedIds.push(ptavID);
            } else {
                selectedIds = selectedIds.filter(ptav => ptav !== ptavID);
            }

        } else {
            selectedIds = [parseInt(ptavId)];
        }
        this.state.product.attribute_lines.find(
            ptal => ptal.id === ptalId
        ).selected_attribute_value_ids = selectedIds;
        this._checkExclusions(this.state.product);
        if (this._isPossibleCombination(this.state.product)) {
            const updatedValues = await this._updateCombination(
                this.state.product, this.state.product.quantity
            );
            Object.assign(this.state.product, updatedValues);
            // When a combination should exist but was deleted from the database, it should not be
            // selectable and considered as an exclusion.
            if (!this.state.product.id && this.state.product.attribute_lines.every(ptal => ptal.create_variant === "always")) {
                const combination = this._getCombination(product);
                this.state.product.archived_combinations = this.state.product.archived_combinations.concat([combination]);
                this._checkExclusions(this.state.product);
            }
        }
    }

    /**
     * Set the custom value for a given custom PTAV.
     *
     * @param {Number} productTmplId - The product template id, as a `product.template` id.
     * @param {Number} ptavId - The PTAV id, as a `product.template.attribute.value` id.
     * @param {String} customValue - The custom value.
     */
    _updatePTAVCustomValue(productTmplId, ptavId, customValue) {
        this.state.product.attribute_lines.find(
            ptal => ptal.selected_attribute_value_ids.includes(ptavId)
        ).customValue = customValue;
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Return the price, in the format of the given currency.
     *
     * @return {String} - The price, in the format of the given currency.
     */
    getFormattedPrice() {
        return formatCurrency(this.state.product.price, this.env.currencyId);
    }

    /**
     * Return the selected PTAV of the product, as a list of `product.template.attribute.value` id.
     *
     * @param {Object} product - The product for which to find the combination.
     * @return {Array} - The combination of the product.
     */
    _getCombination(product) {
        return product.attribute_lines.flatMap(ptal => ptal.selected_attribute_value_ids);
    }

    /**
     * Set the quantity of the product to a given value.
     *
     * @param {Number} quantity - The new quantity of the product.
     */
    async _setQuantity(quantity) {
        if (quantity > 0) {
            const { price } = await this._updateCombination(this.state.product, quantity);
            this.state.product.quantity = quantity;
            this.state.product.price = parseFloat(price);
        }
    }

    /**
     * Check if a product has a valid combination.
     *
     * @param {Object} product - The product for which to check the combination.
     * @return {Boolean} - Whether the combination is valid or not.
     */
    _isPossibleCombination(product) {
        return product.attribute_lines.every(ptal => !ptal.attribute_values.find(
            ptav => ptal.selected_attribute_value_ids.includes(ptav.id)
        )?.excluded);
    }

    /**
     * Check the exclusions of a given product.
     *
     * @param {Object} product - The product for which to check the exclusions.
     */
    _checkExclusions(product) {
        const combination = this._getCombination(product);
        const exclusions = product.exclusions;
        const archivedCombinations = product.archived_combinations;
        const ptavList = product.attribute_lines.flat().flatMap(ptal => ptal.attribute_values)
        ptavList.map(ptav => ptav.excluded = false); // Reset all the values

        if (exclusions) {
            for(const ptavId of combination) {
                for(const excludedPtavId of exclusions[ptavId]) {
                    ptavList.find(ptav => ptav.id === excludedPtavId).excluded = true;
                }
            }
        }
        if (archivedCombinations) {
            for(const excludedCombination of archivedCombinations) {
                const ptavCommon = excludedCombination.filter((ptav) => combination.includes(ptav));
                if (ptavCommon.length === combination.length) {
                    for(const excludedPtavId of ptavCommon) {
                        ptavList.find(ptav => ptav.id === excludedPtavId).excluded = true;
                    }
                } else if (ptavCommon.length === (combination.length - 1)) {
                    // In this case we only need to disable the remaining ptav
                    const disabledPtavId = excludedCombination.find(
                        (ptav) => !combination.includes(ptav)
                    );
                    const excludedPtav = ptavList.find(ptav => ptav.id === disabledPtavId)
                    if (excludedPtav) {
                        excludedPtav.excluded = true;
                    }
                }
            }
        }
    }

    /**
     * Serialize the product into a format understandable by `sale.order.line`.
     * @param {Object} product - The product to serialize.
     * @return {Object} - The serialized product.
     */
    _serializeProduct(product) {
        let serializedProduct = {  //ok
            product_id: product.id,
            product_template_id: product.product_tmpl_id,
            add_qty: product.quantity,
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

        return serializedProduct;
    }

    /**
     * TODO VCR
     *
     */
    async addToCart() {
        const data = await rpc("/shop/cart/update_json", {
            ...this._serializeProduct(this.state.product),
            display: false,
            force_create: true,
        });
        if (data.cart_quantity && (data.cart_quantity !== parseInt($(".my_cart_quantity").text()))) {
            wSaleUtils.updateCartNavBar(data);
        };
        // Show the notification about the cart
        if (data.notification_info.lines) {
            this.cartNotification.add(_t("Item(s) added to your cart"), {
                lines: data.notification_info.lines,
                currency_id: data.notification_info.currency_id,
            });
        }
        if (data.notification_info.warning) {
            this.cartNotification.add(_t("Warning"), {
                warning: data.notification_info.warning,
            });
        }
        return data;
    }
}

registry.category("public_components").add("website_sale.ProductConfigurator", ProductConfigurator);
