/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Widget } from "web.public.widget";
import VariantMixin from "sale.VariantMixin";
import { WebsiteSaleCartButtonParent } from "./website_sale_cart_button";
import { KeepLast } from "@web/core/utils/concurrency";
import { sprintf } from "@web/core/utils/strings";
import { _t } from "web.core";
import { priceToStr } from "./utils";

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
        // Quantity manager
        "change input[name='add_qty']": "onChangeAddQuantity",
        "click .css_quantity a.js_add_cart_json:has(> i.fa-minus)": "decreaseAddQuantity",
        "click .css_quantity a.js_add_cart_json:has(> i.fa-plus)": "increaseAddQuantity",
        // Variant manager
        "change [data-attribute_exclusions]": "onChangeVariant", // Change of attribute
    },

    /**
     * @override
     */
    start() {
        const result = this._super(...arguments);
        this.quantityInput = this.getInput("add_qty");

        // We only care about the last call to get_combination_info.
        const keepLast = new KeepLast();
        // Throttle, we do not need to spam our server.
        const throttledOnChangeOptions = _.throttle(this.onChangeOptions.bind(this), 500);
        this.throttledOnChangeOptions = () => {
            // We keep the last promise in order to be able to await the latest call.
            return (this.combinationDataPromise = keepLast.add(
                throttledOnChangeOptions(this.getCurrentConfiguration())
            ));
        };

        // The page when loaded does not apply exclusion data.
        // Load it ourselves if we have it.
        const options = this.el.querySelector(".js_add_cart_variants[data-attribute_exclusions]");
        if (options) {
            this.checkExclusions();
        }
        return result;
    },

    /**
     * Returns the input for the given name.
     */
    getInput(name) {
        return this.el.querySelector(`input[name=${name}]`);
    },

    /**
     * Query parent widget for more parameters to be passed to the get_combination_info call.
     * //TODO: maybe need async ?
     */
    getCombinationInfoParam(configuration) {
        const params = { ...configuration };
        this.trigger_up("get_combination_info_params", {
            params,
        });
        return params;
    },

    /**
     * Called when the variant has changed or the quantity has changed.
     *
     * Reloads the combination info.
     */
    async onChangeOptions(configuration) {
        const params = this.getCombinationInfoParam(configuration);
        const combinationData = await this._rpc({
            route: "/sale/get_combination_info_website",
            params: {
                ...params,
                parent_combination: false,
                pricelist_id: false,
            },
        });
        // default `is_combination_possible` to true if the key is not available.
        if (!combinationData.hasOwnProperty("is_combination_possible")) {
            combinationData.is_combination_possible = true;
        }
        this.trigger_up("combination_change", {
            combinationData,
        });
        console.log("params", params);
        console.log("combination info", combinationData);
        this.checkExclusions();
        this.onChangeCombination(combinationData);
    },

    onChangeCombination(data) {
        // Disable if not possible.
        this.el.classList.toggle("css_not_available", !data.is_combination_possible);
        this.el
            .querySelectorAll("#add_to_cart, .o_we_buy_now")
            .forEach((node) => node.classList.toggle("disabled", !data.is_combination_possible));

        const priceEl = this.el.querySelector(".oe_price .oe_currency_value");
        const defaultPriceEl = this.el.querySelector(".oe_default_price .oe_currency_value");
        if (priceEl) {
            priceEl.textContent = priceToStr(data.price);
        }
        if (defaultPriceEl) {
            defaultPriceEl.textContent = priceToStr(data.list_price);
        }

        if (data.has_discounted_price) {
            defaultPriceEl.closest(".oe_website_sale").classList.add("discount");
            defaultPriceEl.parentElement.classList.remove("d-none");
        } else {
            defaultPriceEl.closest(".oe_website_sale").classList.remove("discount");
            defaultPriceEl.parentElement.classList.add("d-none");
        }

        const productIdInput = this.getInput("product_id");
        productIdInput.value = data.product_id || 0;
        $(productIdInput).trigger("change");
    },

    /**
     * Returns an object with the current configuration of the product.
     * May contain more values.
     *
     * @returns {{combination: Array<Integer>, add_qty: Integer}}
     */
    getCurrentConfiguration() {
        const combination = [];
        this.el.querySelectorAll("input.js_variant_change:checked, select.js_variant_change").forEach((el) => {
            combination.push(parseInt(el.value));
        });
        const productCustomAttributeValues = [];
        this.el.querySelectorAll(".variant_custom_value").forEach((el) =>{
            productCustomAttributeValues.push({
                custom_product_template_attribute_value_id: el.dataset.custom_product_template_attribute_value_id,
                attribute_value_name: el.dataset.attribute_value_name,
                custom_value: el.value,
            });
        });
        return {
            product_template_id: parseInt(this.getInput("product_template_id").value),
            product_id: parseInt(this.getInput("product_id").value),
            combination,
            product_custom_attribute_values: JSON.stringify(productCustomAttributeValues),
            add_qty: this.getCurrentQuantity(),
        };
    },

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
     * Called when changing the variant configuration.
     */
    onChangeVariant(ev) {
        // No need to trigger if we change a custom value.
        if (!ev.target.classList.contains("variant_custom_value")) {
            this.throttledOnChangeOptions();
        }
        this.handleCustomInput(ev.target);
    },

    /**
     * Add/remove a custom text input if the variant value is custom and checked/unchecked.
     */
    handleCustomInput(variantInput) {
        let variantContainer;
        let customInput;
        if (variantInput.matches("input[type=radio]") && variantInput.checked) {
            variantContainer = variantInput.closest("ul")?.closest("li");
            customInput = variantInput;
        } else if (variantInput.matches("select")) {
            variantContainer = variantInput.cloest("li");
            customInput = variantInput.querySelector(`option[value='${variantInput.value}']`);
        }
        if (!variantContainer) {
            return;
        }
        if (customInput && customInput.dataset.is_custom === "True") {
            const attributeValueId = customInput.dataset.value_id;
            const attributeValueName = customInput.dataset.value_name;
            const customTextInput = variantContainer.querySelector(".variant_custom_value");
            if (!customTextInput || customTextInput.dataset.custom_product_template_attribute_value_id !== attributeValueId) {
                // Create new input.
                customTextInput?.remove();
                const newCustomTextInput = document.createElement("input");
                newCustomTextInput.type = "text";
                newCustomTextInput.placeholder = attributeValueName;
                newCustomTextInput.dataset.custom_product_template_attribute_value_id = attributeValueId;
                newCustomTextInput.dataset.attribute_value_name = attributeValueName;
                newCustomTextInput.classList.add("custom_value_radio",  "variant_custom_value", "form-control", "mt-2");
                variantContainer.appendChild(newCustomTextInput);
                newCustomTextInput.focus();
            }
        } else {
            // Remove old input, input is not checked.
            variantContainer.querySelector(".variant_custom_value")?.remove();
        }
    },

    /**
     * Changing the to add quantity triggers a reload of product information.
     */
    onChangeAddQuantity(ev) {
        console.log("Changed quantity to", this.getCurrentQuantity());
        this.throttledOnChangeOptions();
    },

    /**
     * @returns {Integer} currently selected quantity
     */
    getCurrentQuantity() {
        return parseInt(this.quantityInput.value);
    },

    /**
     * Change the requested quantity
     */
    setAddQuantity(qty) {
        if (this.getCurrentQuantity() === qty) {
            return;
        }
        this.quantityInput.value = qty;
        $(this.quantityInput).trigger("change");
    },

    increaseAddQuantity() {
        this.setAddQuantity(this.getCurrentQuantity() + 1);
    },

    decreaseAddQuantity() {
        this.setAddQuantity(Math.max(this.getCurrentQuantity() - 1, 1));
    },

    /**
     * Get exclusion data from DOM.
     */
    getExclusionData() {
        const options = this.el.querySelector(".js_add_cart_variants[data-attribute_exclusions]");
        if (options) {
            return JSON.parse(options.dataset.attribute_exclusions);
        }
        return {};
    },

    /**
     * Will disable attribute values' inputs based on cominbation exclusions
     * and will disable the "add" button if the selected combination is not
     * available.
     *
     * It will also check that the selected combination does not exactly
     * match a manually archived product.
     */
    checkExclusions() {
        const data = this.getExclusionData();
        // Reset everything
        for (const option of this.el.querySelectorAll("option, input, label, .o_variant_pills")) {
            option.classList.remove("css_not_available");
            option.title = option.dataset.value_name || "";
            Data.set(option, "excluded-by", "");
        }

        const { combination } = this.getCurrentConfiguration();
        // "exclusions": array of ptav
        // for each of them, contains array of other ptav to exclude
        for (const ptav of combination) {
            if (!data.exclusions || !data.exclusions.hasOwnProperty(ptav)) {
                continue;
            }
            for (const otherPtav of data.exclusions[ptav]) {
                this.disableInput(otherPtav, ptav, data.mapped_attribute_names);
            }
        }
        // combination exclusions: array of array of ptav
        // for example a product with 3 variation and one specific variation is disabled (archived)
        // requires the first 2 to be selected for the third to be disabled.
        for (const excludedCombination of data.archived_combinations || []) {
            const commonPtavs = excludedCombination.filter((ptav) => combination.includes(ptav));
            if (ptavCommon.length === combination.length) {
                // Selected combination is archived, all attributes must be disabled from each other.
                for (const ptav of combination) {
                    for (const otherPtav of combination) {
                        if (ptav === otherPtav) {
                            continue;
                        }
                        this.disableInput(otherPtav, ptav, data.mapped_attribute_names);
                    }
                }
            } else if (ptavCommon.length === combination.length - 1) {
                const disabledPtav = excludedCombination.find((ptav) => !combination.includes(ptav));
                for (const ptav of excludedCombination) {
                    if (ptav === disabledPtav) {
                        continue;
                    }
                    this.disableInput(disabledPtav, ptav, data.mapped_attribute_names);
                }
            }
        }
    },

    /**
     * Will disable the input/option that refers to the passed ptav.
     * This is used to show the user that some combinations are not available.
     *
     * It will also change the title of the input to explain why the input is disabled
     * based on excludedBy.
     * e.g: Not available with Color: Black
     */
    disableInput(ptav, excludedBy, attributeNames) {
        const input = this.el.querySelector(`option[value='${ptav}'], input[value='${ptav}']`);
        input.classList.add("css_not_available");
        let label, pill;
        if ((label = input.closest("label"))) {
            label.classList.add("css_not_available");
        }
        if ((pill = input.closest(".o_variant_pills"))) {
            pill.classList.add("css_not_available");
        }
        if (!excludedBy || !attributeNames) {
            return;
        }
        // We modify the title for both the input and the label.
        const targets = (input.matches("option") && [input]) || [input, input.closest("label")];
        let excludedByData = [];
        if (Data.get(input, "excluded-by")) {
            excludedByData = JSON.parse(Data.get(input, "excluded-by"));
        }
        const excludedByName = attributeNames[excludedBy];
        excludedByData.push(excludedByName);

        for (const target of targets) {
            target.title = sprintf(_t("Not available with %s"), excludedByData.join(", "));
        }
        Data.set(input, "excluded-by", JSON.stringify(excludedByData));
    },
});

export const WebsiteSaleOptionsWithCartButton = WebsiteSaleOptions.extend(WebsiteSaleCartButtonParent).extend({
    addToCartButtonSelector: "a#add_to_cart",

    async getProductInfo(ev) {
        if (this.combinationDataPromise) {
            // Make sure our last load is done and applied to the page.
            await this.combinationDataPromise;
        }
        const configuration = this.getCurrentConfiguration();
        // We probably don't need the cart lines to be rendered.
        configuration.display = false;
        ev.data.resolve(configuration);
    },
});
