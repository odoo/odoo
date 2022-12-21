/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Widget } from "web.public.widget";
import VariantMixin from "sale.VariantMixin";
import { WebsiteSaleCartButtonParent } from "./website_sale_cart_button";

/**
 * Patch actual VariantMixin as it is used by the product configurator.
 * TODO: check if ok to move in `website_sale_product_configurator`. -> seems only used there.
 */

patch(VariantMixin, "@website_sale/frontend/website_sale_variant", {
    /**
     * Website behavior is slightly different from backend so we append
     * "_website" to URLs to lead to a different route
     *
     * @private
     * @param {string} uri The uri to adapt
     */
    _getUri(uri) {
        if (this.isWebsite) {
            return uri + "_website";
        }
        return this._super(...arguments);
    },

    /**
     * @override
     */
    _onChangeCombination(ev, $parent, combination) {
        const $pricePerUom = $parent.find(".o_base_unit_price:first .oe_currency_value");
        if ($pricePerUom) {
            if (combination.is_combination_possible !== false && combination.base_unit_price != 0) {
                $pricePerUom.parents(".o_base_unit_price_wrapper").removeClass("d-none");
                $pricePerUom.text(this._priceToStr(combination.base_unit_price));
                $parent.find(".oe_custom_base_unit:first").text(combination.base_unit_name);
            } else {
                $pricePerUom.parents(".o_base_unit_price_wrapper").addClass("d-none");
            }
        }

        // Triggers a new JS event with the correct payload, which is then handled
        // by the google analytics tracking code.
        // Indeed, every time another variant is selected, a new view_item event
        // needs to be tracked by google analytics.
        if ("product_tracking_info" in combination) {
            const $product = $("#product_detail");
            $product.data("product-tracking-info", combination["product_tracking_info"]);
            $product.trigger("view_item_event", combination["product_tracking_info"]);
        }
        const addToCart = $parent.find("#add_to_cart_wrap");
        const contactUsButton = $parent.find("#contact_us_wrapper");
        const productPrice = $parent.find(".product_price");
        const quantity = $parent.find(".css_quantity");
        const product_unavailable = $parent.find("#product_unavailable");
        if (combination.prevent_zero_price_sale) {
            productPrice.removeClass("d-inline-block").addClass("d-none");
            quantity.removeClass("d-inline-flex").addClass("d-none");
            addToCart.removeClass("d-inline-flex").addClass("d-none");
            contactUsButton.removeClass("d-none").addClass("d-flex");
            product_unavailable.removeClass("d-none").addClass("d-flex");
        } else {
            productPrice.removeClass("d-none").addClass("d-inline-block");
            quantity.removeClass("d-none").addClass("d-inline-flex");
            addToCart.removeClass("d-none").addClass("d-inline-flex");
            contactUsButton.removeClass("d-flex").addClass("d-none");
            product_unavailable.removeClass("d-flex").addClass("d-none");
        }
        this._super(...arguments);
    },

    /**
     * Toggles the disabled class depending on the $parent element
     * and the possibility of the current combination. This override
     * allows us to disable the secondary button in the website
     * sale product configuration modal.
     *
     * @override
     * @private
     * @param {$.Element} $parent
     * @param {boolean} isCombinationPossible
     */
    _toggleDisable($parent, isCombinationPossible) {
        if ($parent.hasClass("in_cart")) {
            const secondaryButton = $parent.parents(".modal-content").find(".modal-footer .btn-secondary");
            secondaryButton.prop("disabled", !isCombinationPossible);
            secondaryButton.toggleClass("disabled", !isCombinationPossible);
        }
        this._super(...arguments);
    },
});

/**
 * @typedef {Object} ProductOptions
 * @property {Array} combination - list of ids for the combination.
 * @property {Integer} add_qty - quantity to add
 */

/**
 * Widget version of VariantMixin.
 * This widget represents an attribute selector for a product.
 *
 * Widget is not standalone and has to be initialized manually.
 * The following custom events can be implemented in the parent:
 *  - get_combination_info_params: provide more optional parameters for the get_combination_info call.
 *
 * The following events are triggered and can be listened to:
 *  - combination_change: called after the combination information is loaded.
 *
 * REMOVE ME: rationale behind doing a completely new variant mixin equivalent:
 *  The current one is mainly used for eCommerce (badly) and for the
 *  product configurator (for which it was designed) however the mixin will make no sense
 *  if the configurator ever gets completely updated to owl (which it should).
 *  Meaning eCommerce will need its alternative right away and making our own solution is viable.
 */

export const WebsiteSaleOptions = Widget.extend({
    events: {
        "change .css_attribute_color input": "onChangeColorAttribute", // Visual
        "change input#add_qty": "onChangeAddQuantity",
        "click .css_quantity a.js_add_cart_json > i.fa-minus": 
        "change [data-attribute_exclusions]": "onChangeVariant", // Change of attribute
    },


    /**
     * @override
     */
    start() {
        const result = this._super(...arguments);
        this.quantityInput = this.el.querySelector("input[name='add_qty']");
        return result;
    },

    /**
     * Query parent widget if more information needs to be loaded
     * from the get_combination_info rpc request.
     * //TODO: giving the params might be a bit confusing as it will NOT contain information from overrides
     *
     * @override
     */
    getOptionalCombinationInfoParam($product) {
        const params = this._super(...arguments);
        this.trigger_up("get_combination_info_params", {
            params,
        });
        return params;
    },

    /**
     *
     *
     * @override
     */
    onChangeCombination(ev, $parent, combination) {},

    /**
     * Highlight selected color.
     */
    onChangeColorAttribute(ev) {
        this.el.querySelectorAll(".css_attribute_color.active").forEach((el) => el.classList.remove("active"));
        const checkedInput = this.el.querySelector(".css_attribute_color:has(input:checked)");
        if (checkedInput) {
            checkedInput.classList.add("active");
        }
    },

    /**
     *
     */
    onChangeVariant(ev) {
        console.log("Changed variant");
    },

    /**
     * @returns {Integer} currently selected quantity
     */
    getCurrentQuantity() {
        return parseInt(this.quantityInput.value);
    },

    /**
     * Changing the to add quantity triggers a reload of product information.
     */
    onChangeAddQuantity(ev) {
        console.log("Changed quantity to", this.getCurrentQuantity());
    },

    /**
     * Returns an object with the current configuration of the product.
     *
     * @returns {{combination: Array<Integer>, add_qty: Integer}}
     */
    getCurrentConfiguration() {
        const combination = [];
        this.el.querySelectorAll("input.js_variant_change:checked, select.js_variant_change").forEach((el) => {
            // String -> Integer
            combination.push(parseInt(el.value));
        });
        return {
            combination,
            add_qty: this.getCurrentQuantity(),
        };
    },
});

export const WebsiteSaleOptionsWithCartButton = WebsiteSaleOptions.extend(WebsiteSaleCartButtonParent).extend({
    addToCartButtonSelector: "a#add_to_cart",

    async getProductInfo(ev) {
        const configuration = this.getCurrentConfiguration();
        ev.data.resolve({
            product_id: 1,
            add_qty: configuration.add_qty,
            combination: configuration.combination,
        });
    },
});
