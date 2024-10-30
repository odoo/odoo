import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { KeepLast } from "@web/core/utils/concurrency";
import { memoize, uniqueId } from "@web/core/utils/functions";
import { insertThousandsSep } from "@web/core/utils/numbers";
import { throttleForAnimation } from "@web/core/utils/timing";

var VariantMixin = {
    events: {
        'change .css_attribute_color input': '_onChangeColorAttribute',
        'click .o_variant_pills': '_onChangePillsAttribute',
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * When a variant is changed, this will check:
     * - If the selected combination is available or not
     * - The extra price if applicable
     * - The display name of the product ("Customizable desk (White, Steel)")
     * - The new total price
     * - The need of adding a "custom value" input
     *   If the custom value is the only available value
     *   (defined by its data 'is_single_and_custom'),
     *   the custom value will have it's own input & label
     *
     * 'change' events triggered by the user entered custom values are ignored since they
     * are not relevant
     *
     * @param {MouseEvent} ev
     */
    onChangeVariant: function (ev) {
        const parentEl = ev.target.closest(".js_product");
        if (!parentEl.dataset.uniqueId) {
            parentEl.dataset.uniqueId = uniqueId();
        }
        this._throttledGetCombinationInfo(this, parseInt(parentEl.dataset.uniqueId))(ev);
    },
    /**
     * @see onChangeVariant
     *
     * @private
     * @param {Event} ev
     * @returns {Deferred}
     */
    _getCombinationInfo: function (ev) {
        if (ev.target?.classList.contains("variant_custom_value")) {
            return Promise.resolve();
        }

        const parentEl = ev.target?.closest(".js_product");
        if (!parentEl) {
            return Promise.resolve();
        }
        const combination = this.getSelectedVariantValues(parentEl);

        return rpc('/website_sale/get_combination_info', {
            'product_template_id': parseInt(parentEl.querySelector(".product_template_id").value),
            'product_id': this._getProductId(parentEl),
            'combination': combination,
            'add_qty': parseInt(parentEl.querySelector('input[name="add_qty"]').value),
            'context': this.context,
            ...this._getOptionalCombinationInfoParam(parentEl),
        }).then((combinationData) => {
            if (this._shouldIgnoreRpcResult()) {
                return;
            }
            this._onChangeCombination(ev, parentEl, combinationData);
            this._checkExclusions(parentEl, combination);
        });
    },

    /**
     * Hook to add optional info to the combination info call.
     *
     * @param {Element} product
     */
    _getOptionalCombinationInfoParam(product) {
        return {};
    },

    /**
     * Will add the "custom value" input for this attribute value if
     * the attribute value is configured as "custom" (see product_attribute_value.is_custom)
     *
     * @private
     * @param {HTMLElement} target
     */
    handleCustomValues(target) {
        let variantContainerEl;
        let customInput = false;

        if (target.matches("input[type=radio]") && target.checked) {
            variantContainerEl = target.closest("ul")?.closest("li");
            customInput = target;
        } else if (target.tagName === "SELECT") {
            variantContainerEl = target.closest("li");
            customInput = target.querySelector('option[value="' + target.value + '"]');
        }

        if (variantContainerEl) {
            if (customInput && customInput.dataset.is_custom === "True") {
                const attributeValueId = customInput.dataset.value_id;
                const attributeValueName = customInput.dataset.value_name;

                if (
                    variantContainerEl.querySelector(".variant_custom_value") ||
                    variantContainerEl.querySelector(".variant_custom_value")?.dataset
                        .customProductTemplateAttributeValueId !== parseInt(attributeValueId)
                ) {
                    variantContainerEl
                        .querySelectorAll(".variant_custom_value")
                        .forEach((el) => el.remove());

                    const previousCustomValue = customInput.getAttribute("previous_custom_value");
                    const inputEl = document.createElement("input");
                    inputEl.type = "text";
                    inputEl.dataset.customProductTemplateAttributeValueId = attributeValueId;
                    inputEl.dataset.attributeValueName = attributeValueName;
                    inputEl.classList.add("variant_custom_value", "form-control", "mt-2");

                    inputEl.setAttribute("placeholder", attributeValueName);
                    inputEl.classList.add("custom_value_radio");
                    variantContainerEl.append(inputEl);
                    if (previousCustomValue) {
                        inputEl.value = previousCustomValue;
                    }
                }
            } else {
                variantContainerEl
                    .querySelectorAll(".variant_custom_value")
                    .forEach((el) => el.remove());
            }
        }
    },

    /**
     * Hack to add and remove from cart with json
     *
     * @param {MouseEvent} ev
     */
    onClickAddCartJSON: function (ev) {
        ev.preventDefault();
        const link = ev.currentTarget;
        const inputEl = link.closest(".input-group").querySelector("input");
        const min = parseFloat(inputEl.dataset.min || 0);
        const max = parseFloat(inputEl.dataset.max || Infinity);
        const previousQty = parseFloat(inputEl.value || 0, 10);
        const quantity = (link.querySelector("i.fa-minus") ? -1 : 1) + previousQty;
        const newQty = quantity > min ? (quantity < max ? quantity : max) : min;

        if (newQty !== previousQty) {
            inputEl.value = newQty;
            inputEl.dispatchEvent(new Event("change", { bubbles: true }));
        }
        return false;
    },

    /**
     * When the quantity is changed, we need to query the new price of the product.
     * Based on the pricelist, the price might change when quantity exceeds a certain amount.
     *
     * @param {MouseEvent} ev
     */
    onChangeAddQuantity: function (ev) {
        const parentEl = ev.currentTarget.closest("form");
        if (parentEl) {
            this.triggerVariantChange(parentEl);
        }
    },

    /**
     * Triggers the price computation and other variant specific changes
     *
     * @param {Element} container
     */
    triggerVariantChange(container) {
        container
            .querySelector("ul[data-attribute_exclusions]")
            ?.dispatchEvent(new Event("change", { bubbles: true }));
        container
            .querySelectorAll("input.js_variant_change:checked, select.js_variant_change")
            .forEach((el) => {
                VariantMixin.handleCustomValues(el);
            });
    },

    /**
     * Will look for user custom attribute values
     * in the provided container
     *
     * @param {Element} container
     * @returns {Array} array of custom values with the following format
     *   {integer} custom_product_template_attribute_value_id
     *   {string} attribute_value_name
     *   {string} custom_value
     */
    getCustomVariantValues(container) {
        const variantCustomValues = [];

        if (!container) {
            return variantCustomValues;
        }

        container.querySelectorAll(".variant_custom_value").forEach((variantCustomValueInput) => {
            if (variantCustomValueInput) {
                variantCustomValues.push({
                    'custom_product_template_attribute_value_id': parseInt(
                        variantCustomValueInput.dataset.customProductTemplateAttributeValueId
                    ),
                    'attribute_value_name': variantCustomValueInput.dataset.attributeValueName,
                    'custom_value': variantCustomValueInput.value,
                });
            }
        });

        return variantCustomValues;
    },

    /**
     * Will look for attribute values that do not create product variant
     * (see product_attribute.create_variant "dynamic")
     *
     * @param {Element} container
     * @returns {Array} array of attribute values with the following format
     *   {integer} custom_product_template_attribute_value_id
     *   {string} attribute_value_name
     *   {integer} value
     *   {string} attribute_name
     *   {boolean} is_custom
     */
    getNoVariantAttributeValues(container) {
        var noVariantAttributeValues = [];
        var variantsValuesSelectors = [
            'input.no_variant.js_variant_change:checked',
            'select.no_variant.js_variant_change'
        ];

        if (!container) {
            return noVariantAttributeValues;
        }

        container.querySelectorAll(variantsValuesSelectors.join(",")).forEach((variantValueInput) => {
            const singleNoCustom = variantValueInput.dataset.isSingle && !variantValueInput.dataset.isCustom;

            if (variantValueInput.tagname === "SELECT") {
                variantValueInput = variantValueInput.querySelector(
                    "option[value=" + variantValueInput.value + "]"
                );
            }

            if (variantValueInput && !singleNoCustom) {
                noVariantAttributeValues.push({
                    'custom_product_template_attribute_value_id': parseInt(variantValueInput.dataset.valueId),
                    'attribute_value_name': variantValueInput.dataset.valueName,
                    'value': variantValueInput.value,
                    'attribute_name': variantValueInput.dataset.attributeName,
                    'is_custom': variantValueInput.dataset.isCustom,
                });
            }
        });

        return noVariantAttributeValues;
    },

    /**
     * Will return the list of selected product.template.attribute.value ids
     *
     * @param {Element} containerEl the container to look into
     */
    getSelectedVariantValues(containerEl) {
        const values = [];

        const variantsValuesSelectors = [
            "input.js_variant_change:checked",
            "select.js_variant_change",
        ];
        containerEl?.querySelectorAll(variantsValuesSelectors.join(", ")).forEach((el) => {
            values.push(+el.value);
        });

        return values;
    },

    /**
     * Will return a promise:
     *
     * - If the product already exists, immediately resolves it with the product_id
     * - If the product does not exist yet ("dynamic" variant creation), this method will
     *   create the product first and then resolve the promise with the created product's id
     *
     * @param {Element} container the container to look into
     * @param {integer} productId the product id
     * @param {integer} productTemplateId the corresponding product template id
     * @returns {Promise} the promise that will be resolved with a {integer} productId
     */
    selectOrCreateProduct(containerEl, productId, productTemplateId) {
        productId = parseInt(productId);
        productTemplateId = parseInt(productTemplateId);
        var productReady = Promise.resolve();
        if (productId) {
            productReady = Promise.resolve(productId);
        } else {
            var params = {
                product_template_id: productTemplateId,
                product_template_attribute_value_ids:
                    JSON.stringify(VariantMixin.getSelectedVariantValues(containerEl)),
            };

            var route = '/sale/create_product_variant';
            productReady = rpc(route, params);
        }

        return productReady;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Will disable attribute value's inputs based on combination exclusions
     * and will disable the "add" button if the selected combination
     * is not available
     *
     * This will check both the exclusions within the product itself and
     * the exclusions coming from the parent product (meaning that this product
     * is an option of the parent product)
     *
     * It will also check that the selected combination does not exactly
     * match a manually archived product
     *
     * @private
     * @param {Element} parentEl the parent container to apply exclusions
     * @param {Array} combination the selected combination of product attribute values
     */
    _checkExclusions(parentEl, combination) {
        var self = this;
        const combinationData = JSON.parse(
            parentEl.querySelector("ul[data-attribute_exclusions]").dataset.attribute_exclusions
        );

        const elements = parentEl.querySelectorAll("option, input, label, .o_variant_pills");
        elements.forEach((el) => {
            el.classList.remove("css_not_available");
            el.title = el.dataset.value_name || "";
            el.dataset.excludedBy = "";
        });

        // exclusion rules: array of ptav
        // for each of them, contains array with the other ptav they exclude
        if (combinationData.exclusions) {
            // browse all the currently selected attributes
            Object.values(combination).forEach((current_ptav) => {
                if (combinationData.exclusions.hasOwnProperty(current_ptav)) {
                    // for each exclusion of the current attribute:
                    Object.values(combinationData.exclusions[current_ptav]).forEach((excluded_ptav) => {
                        // disable the excluded input (even when not already selected)
                        // to give a visual feedback before click
                        self._disableInput(
                            parentEl,
                            excluded_ptav,
                            current_ptav,
                            combinationData.mapped_attribute_names
                        );
                    });
                }
            });
        }
        // combination exclusions: array of array of ptav
        // for example a product with 3 variation and one specific variation is disabled (archived)
        //  requires the first 2 to be selected for the third to be disabled
        if (combinationData.archived_combinations) {
            combinationData.archived_combinations.forEach((excludedCombination) => {
                const ptavCommon = excludedCombination.filter((ptav) => combination.includes(ptav));
                if (
                    !!ptavCommon
                    && (combination.length === excludedCombination.length)
                    && (ptavCommon.length === combination.length)
                ) {
                    // Selected combination is archived, all attributes must be disabled from each other
                    combination.forEach((ptav) => {
                        combination.forEach((ptavOther) => {
                            if (ptav === ptavOther) {
                                return;
                            }
                            self._disableInput(
                                parentEl,
                                ptav,
                                ptavOther,
                                combinationData.mapped_attribute_names,
                            );
                        })
                    })
                } else if (
                    !!ptavCommon
                    && (combination.length === excludedCombination.length)
                    && (ptavCommon.length === (combination.length - 1))
                ) {
                    // In this case we only need to disable the remaining ptav
                    const disabledPtav = excludedCombination.find((ptav) => !combination.includes(ptav));
                    excludedCombination.forEach((ptav) => {
                        if (ptav === disabledPtav) {
                            return;
                        }
                        self._disableInput(
                            parentEl,
                            disabledPtav,
                            ptav,
                            combinationData.mapped_attribute_names,
                        )
                    });
                }
            });
        }
    },
    /**
     * Extracted to a method to be extendable by other modules
     *
     * @param {Element} parentEl
     */
    _getProductId(parentEl) {
        return parseInt(parentEl.querySelector(".product_id").value);
    },
    /**
     * Will disable the input/option that refers to the passed attributeValueId.
     * This is used for showing the user that some combinations are not available.
     *
     * It will also display a message explaining why the input is not selectable.
     * Based on the "excludedBy" and the "productName" params.
     * e.g: Not available with Color: Black
     *
     * @private
     * @param {Element} parentEl
     * @param {integer} attributeValueId
     * @param {integer} excludedBy The attribute value that excludes this input
     * @param {Object} attributeNames A dict containing all the names of the attribute values
     *   to show a human readable message explaining why the input is disabled.
     * @param {string} [productName] The parent product. If provided, it will be appended before
     *   the name of the attribute value that excludes this input
     *   e.g: Not available with Customizable Desk (Color: Black)
     */
    _disableInput(parentEl, attributeValueId, excludedBy, attributeNames, productName) {
        const inputEl = parentEl.querySelector(
            `option[value='${attributeValueId}'], input[value='${attributeValueId}']`
        );
        const labelEl = inputEl.closest("label");
        inputEl.classList.add("css_not_available");
        labelEl.classList.add("css_not_available");
        inputEl.closest(".o_variant_pills")?.classList.add("css_not_available");

        if (excludedBy && attributeNames) {
            const targetEl = inputEl.tagName === "OPTION" ? inputEl : labelEl;
            if (targetEl === labelEl) {
                labelEl.querySelector("div")?.prepend(inputEl);
            }

            var excludedByData = [];
            if (targetEl.dataset.excludedBy) {
                excludedByData = JSON.parse(targetEl.dataset.excludedBy);
            }

            var excludedByName = attributeNames[excludedBy];
            if (productName) {
                excludedByName = productName + ' (' + excludedByName + ')';
            }
            excludedByData.push(excludedByName);

            targetEl.setAttribute("title", _t("Not available with %s", excludedByData.join(", ")));
            targetEl.dataset.excludedBy = JSON.stringify(excludedByData);
        }
    },
    /**
     * @see onChangeVariant
     *
     * @private
     * @param {MouseEvent} ev
     * @param {Element} parentEl
     * @param {Array} combination
     */
    _onChangeCombination(ev, parentEl, combination) {
        const isCombinationPossible = !!combination.is_combination_possible;
        const pricePerUomEl = parentEl.querySelector(".o_base_unit_price .oe_currency_value");
        if (pricePerUomEl) {
            if (isCombinationPossible && combination.base_unit_price != 0) {
                pricePerUomEl.closest(".o_base_unit_price_wrapper").classList.remove("d-none");
                pricePerUomEl.textContent = this._priceToStr(combination.base_unit_price);
                parentEl.querySelector(".oe_custom_base_unit").textContent =
                    combination.base_unit_name;
            } else {
                pricePerUomEl.closest(".o_base_unit_price_wrapper").classList.add("d-none");
            }
        }

        // Triggers a new JS event with the correct payload, which is then handled
        // by the google analytics tracking code.
        // Indeed, every time another variant is selected, a new view_item event
        // needs to be tracked by google analytics.
        if ('product_tracking_info' in combination) {
            const productEl = document.getElementById("product_detail");
            productEl.dataset.productTrackingInfo = JSON.stringify(
                combination["product_tracking_info"]
            );
            productEl.dispatchEvent(
                new CustomEvent("view_item_event", { detail: combination["product_tracking_info"] })
            );
        }
        const addToCartEl = parentEl.querySelector("#add_to_cart_wrap");
        const contactUsButtonEl = parentEl.querySelector("#contact_us_wrapper");
        const productPriceEl = parentEl.querySelector(".product_price");
        const quantityEl = parentEl.querySelector(".css_quantity");
        const product_unavailable = parentEl.querySelector("#product_unavailable");
        if (combination.prevent_zero_price_sale) {
            productPriceEl.classList.remove("d-inline-block");
            productPriceEl.classList.add("d-none");

            quantityEl.classList.remove("d-inline-flex");
            quantityEl.classList.add("d-none");

            addToCartEl.classList.remove("d-inline-flex");
            addToCartEl.classList.add("d-none");

            contactUsButtonEl?.classList.remove("d-none");
            contactUsButtonEl?.classList.add("d-flex");

            product_unavailable.classList.remove("d-none");
            product_unavailable.classList.add("d-flex");
        } else {
            productPriceEl.classList.remove("d-none");
            productPriceEl.classList.add("d-inline-block");

            quantityEl.classList.remove("d-none");
            quantityEl.classList.add("d-inline-flex");

            addToCartEl.classList.remove("d-none");
            addToCartEl.classList.add("d-inline-flex");

            contactUsButtonEl?.classList.remove("d-flex");
            contactUsButtonEl?.classList.add("d-none");

            product_unavailable.classList.remove("d-flex");
            product_unavailable.classList.add("d-none");
        }

        var self = this;
        const price = parentEl.querySelector(".oe_price .oe_currency_value");
        const default_price = parentEl.querySelector(".oe_default_price .oe_currency_value");
        const compare_price = parentEl.querySelector(".oe_compare_list_price");
        price.textContent = self._priceToStr(combination.price);
        if (default_price) {
            default_price.textContent = self._priceToStr(combination.list_price);
        }

        this._toggleDisable(parentEl, isCombinationPossible);

        if (combination.has_discounted_price && !combination.compare_list_price) {
            default_price?.closest(".oe_website_sale").classList.add("discount");
            default_price?.parentElement.classList.remove("d-none");
            compare_price?.classList.add("d-none");
        } else {
            default_price?.closest(".oe_website_sale").classList.remove("discount");
            default_price?.parentElement.classList.add("d-none");
            compare_price?.classList.remove("d-none");
        }

        // update images & tags only when changing product
        // or when either ids are 'false', meaning dynamic products.
        // Dynamic products don't have images BUT they may have invalid
        // combinations that need to disable the image.
        if (!combination.no_product_change) {
            const rootComponentSelectors = ['tr.js_product', '.oe_website_sale'];
            self._updateProductImage(
                parentEl.closest(rootComponentSelectors.join(", ")),
                combination.display_image,
                combination.product_id,
                combination.product_template_id,
                combination.carousel,
                isCombinationPossible
            );
            const productTagEl = parentEl.querySelector(".o_product_tags");
            if (productTagEl) {
                productTagEl.innerHTML = combination.product_tags;
            }
        }

        const productIdElement = parentEl.querySelector(".product_id");
        if (productIdElement) {
            productIdElement.value = combination.product_id || 0;
            productIdElement.dispatchEvent(new Event("change", { bubbles: true }));
        }

        this.handleCustomValues(ev.target);
    },

    /**
     * returns the formatted price
     *
     * @private
     * @param {float} price
     */
    _priceToStr: function (price) {
        var precision = 2;

        const precisionEls = this.el.querySelectorAll(".decimal_precision");
        const lastElement = precisionEls[precisionEls.length - 1];
        if (precisionEls.length) {
            precision = parseInt(lastElement.dataset.precision);
        }
        var formatted = price.toFixed(precision).split(".");
        const { thousandsSep, decimalPoint, grouping } = localization;
        formatted[0] = insertThousandsSep(formatted[0], thousandsSep, grouping);
        return formatted.join(decimalPoint);
    },
    /**
     *
     * The leading execution is to keep good reactivity on the first call, for
     * a better user experience. The trailing is because ultimately only the
     * information about the last selected combination is useful. All
     * intermediary rpc can be ignored and are therefore best not done at all.
     *
     * The keepLast is to make sure we only consider the result of the last call, when several
     * (asynchronous) calls are done in parallel.
     *
     * @private
     * @param {string} uniqueId
     * @returns {function}
     */
    _throttledGetCombinationInfo: memoize(function (self, uniqueId) {
        const keepLast = new KeepLast();
        var _getCombinationInfo = throttleForAnimation(self._getCombinationInfo.bind(self));
        return (ev, params) => keepLast.add(_getCombinationInfo(ev, params));
    }),
    /**
     * Toggles the disabled class depending on the parent element
     * and the possibility of the current combination.
     *
     * @private
     * @param {Element} parentEl
     * @param {boolean} isCombinationPossible
     */
    _toggleDisable(parentEl, isCombinationPossible) {
        parentEl?.classList.toggle("css_not_available", !isCombinationPossible);
    },
    /**
     * Updates the product image.
     * This will use the productId if available or will fallback to the productTemplateId.
     *
     * @private
     * @param {Element} productContainer
     * @param {boolean} displayImage will hide the image if true. It will use the 'invisible' class
     *   instead of d-none to prevent layout change
     * @param {integer} product_id
     * @param {integer} productTemplateId
     */
    _updateProductImage(productContainerEl, displayImage, productId, productTemplateId) {
        const model = productId ? "product.product" : "product.template";
        const modelId = productId || productTemplateId;
        const imageUrl =
            "/web/image/{0}/{1}/" +
            (this._productImageField ? this._productImageField : "image_1024");
        const imageSrc = imageUrl.replace("{0}", model).replace("{1}", modelId);

        var imagesSelectors = [
            'span[data-oe-model^="product."][data-oe-type="image"] img:first-child',
            'img.product_detail_img',
        ];

        const imgEl = productContainerEl.querySelector(imagesSelectors.join(", "));

        if (displayImage) {
            imgEl.classList.remove("invisible");
            imgEl.setAttribute("src", imageSrc);
        } else {
            imgEl.classList.add("invisible");
        }
    },

    /**
     * Highlight selected color
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onChangeColorAttribute: function (ev) {
        const parentEl = ev.target.closest(".js_product");
        const colorElements = parentEl.querySelectorAll(".css_attribute_color");
        colorElements.forEach((el) => {
            el.classList.remove("active");
            if (el.querySelector("input:checked")) {
                el.classList.add("active");
            }
        });
    },

    _onChangePillsAttribute: function (ev) {
        const radio = ev.target.closest(".o_variant_pills").querySelector("input");
        radio.click(); // Trigger onChangeVariant.
        const parentEl = ev.target.closest(".js_product");
        const variantPillEls = parentEl.querySelectorAll(".o_variant_pills");
        variantPillEls.forEach((el) => {
            el.classList.remove("active");
            if (el.querySelector("input:checked")) {
                el.classList.add("active");
            }
        });
    },

    /**
     * Return true if the current object has been destroyed. Useful to know if
     * the result of a rpc should be handled.
     *
     * @private
     */
    _shouldIgnoreRpcResult() {
        return (typeof this.isDestroyed === "function" && this.isDestroyed());
    },

    /**
     * Extension point for website_sale
     *
     * @private
     * @param {string} uri The uri to adapt
     */
    _getUri: function (uri) {
        return uri;
    }
};

export default VariantMixin;
