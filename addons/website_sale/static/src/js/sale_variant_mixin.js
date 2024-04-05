/** @odoo-module **/

import { KeepLast } from "@web/core/utils/concurrency";
import { memoize, uniqueId } from "@web/core/utils/functions";
import { throttleForAnimation } from "@web/core/utils/timing";
import { insertThousandsSep } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";
import { localization } from "@web/core/l10n/localization";
import { rpc } from "@web/core/network/rpc";

var VariantMixin = {
    events: {
        'change .css_attribute_color input': '_onChangeColorAttribute',
        'change .o_variant_pills input' :'_onChangePillsAttribute',
        'change .main_product:not(.in_cart) input.js_quantity': 'onChangeAddQuantity',
        'change [data-attribute_exclusions]': 'onChangeVariant'
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
        const parent = ev.target.closest('.js_product');
        if (parent.dataset.uniqueId) {
            parent.dataset.uniqueId = uniqueId();
        }
        this._throttledGetCombinationInfo(this, parent.dataset.uniqueId)(ev);
    },
    /**
     * @see onChangeVariant
     *
     * @private
     * @param {Event} ev
     * @returns {Deferred}
     */
    _getCombinationInfo: function (ev) {
        if (ev.target.classList.contains('variant_custom_value')) {
            return Promise.resolve();
        }

        const parent = ev.target.closest('.js_product');
        if(!parent.length){
            return Promise.resolve();
        }
        const combination = this.getSelectedVariantValues(parent);
        let parentCombination;
        if (parent.classList.contains('main_product')) {
            parentCombination = JSON.parse(parent.querySelector('ul[data-attribute_exclusions]').dataset.attributeExclusions).parent_combination;
            const optProducts = parent.parentElement.querySelectorAll(`[data-parent-unique-id='${parent.dataset.uniqueId}']`);

            for (const optionalProduct of optProducts) {
                const currentOptionalProduct = optionalProduct;
                const childCombination = this.getSelectedVariantValues(currentOptionalProduct);
                const productTemplateId = parseInt(currentOptionalProduct.querySelector('.product_template_id').value);
                rpc('/website_sale/get_combination_info', {
                    'product_template_id': productTemplateId,
                    'product_id': this._getProductId(currentOptionalProduct),
                    'combination': childCombination,
                    'add_qty': parseInt(currentOptionalProduct.querySelector('input[name="add_qty"]').value),
                    'parent_combination': combination,
                    'context': this.context,
                    ...this._getOptionalCombinationInfoParam(currentOptionalProduct),
                }).then((combinationData) => {
                    if (this._shouldIgnoreRpcResult()) {
                        return;
                    }
                    this._onChangeCombination(ev, currentOptionalProduct, combinationData);
                    this._checkExclusions(currentOptionalProduct, childCombination, combinationData.parent_exclusions);
                });
            }
        } else {
            parentCombination = this.getSelectedVariantValues(
                parent.parentElement.querySelector('.js_product.in_cart.main_product')
            );
        }

        return rpc('/website_sale/get_combination_info', {
            'product_template_id': parseInt(parent.querySelector('.product_template_id').value),
            'product_id': this._getProductId(parent),
            'combination': combination,
            'add_qty': parseInt(parent.querySelector('input[name="add_qty"]').value),
            'parent_combination': parentCombination,
            'context': this.context,
            ...this._getOptionalCombinationInfoParam(parent),
        }).then((combinationData) => {
            if (this._shouldIgnoreRpcResult()) {
                return;
            }
            this._onChangeCombination(ev, parent, combinationData);
            this._checkExclusions(parent, combination, combinationData.parent_exclusions);
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
     * @param {MouseEvent} ev
     */
    handleCustomValues: function (target) {
        let variantContainer;
        let customInput = false;
        if (target.matches('input[type=radio]') && target.checked) {
            variantContainer = target.closest('ul').closest('li');
            customInput = target;
        } else if (target.tagName === 'SELECT') {
            variantContainer = target.closest('li');
            customInput = target
                .querySelector('option[value="' + target.value + '"]');
        }

        if (variantContainer) {
            if (customInput && customInput.dataset.is_custom === 'True') {
                const attributeValueId = customInput.dataset.value_id;
                const attributeValueName = customInput.dataset.value_name;

                if (variantContainer.querySelector('.variant_custom_value').length === 0
                        || variantContainer
                            .querySelector('.variant_custom_value')
                            .dataset.customProductTemplateAttributeValueId !== parseInt(attributeValueId)) {
                    variantContainer.querySelectorAll('.variant_custom_value').forEach((el) => el.remove());

                    const previousCustomValue = customInput.getAttribute("previous_custom_value");
                    const input = document.createElement('input');
                    input.type = 'text';
                    input.dataset.customProductTemplateAttributeValueId = attributeValueId;
                    input.dataset.attributeValueName = attributeValueName;
                    input.classList.add('variant_custom_value', 'form-control', 'mt-2');

                    input.setAttribute('placeholder', attributeValueName);
                    input.classList.add('custom_value_radio');
                    variantContainer.append(input);
                    if (previousCustomValue) {
                        input.value = previousCustomValue;
                    }
                }
            } else {
                variantContainer.querySelectorAll('.variant_custom_value').forEach((el) => el.remove());
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
        var link = ev.currentTarget;
        var input = link.closest('.input-group').querySelector("input");
        var min = parseFloat(input.dataset.min || 0);
        var max = parseFloat(input.dataset.max || Infinity);
        var previousQty = parseFloat(input.value || 0, 10);
        var quantity = (link.querySelector('.fa-minus').length ? -1 : 1) + previousQty;
        var newQty = quantity > min ? (quantity < max ? quantity : max) : min;

        if (newQty !== previousQty) {
            input.value = newQty;
            input.dispatchEvent(new Event('change'));
        }
        return false;
    },

    /**
     * When the quantity is changed, we need to query the new price of the product.
     * Based on the price list, the price might change when quantity exceeds X
     *
     * @param {MouseEvent} ev
     */
    onChangeAddQuantity: function (ev) {
        let parent;
        if (ev.currentTarget.closest('.oe_advanced_configurator_modal').length > 0){
            parent = ev.currentTarget.closest('.oe_advanced_configurator_modal');
        } else if (ev.currentTarget.closest('form').length > 0){
            parent = ev.currentTarget.closest('form');
        }  else {
            parent = ev.currentTarget.closest('.o_product_configurator');
        }

        this.triggerVariantChange(parent);
    },

    /**
     * Triggers the price computation and other variant specific changes
     *
     * @param {Element} container
     */
    triggerVariantChange: function (container) {
        container.querySelector('ul[data-attribute_exclusions]').dispatchEvent(new Event('change'));
        container.querySelectorAll('input.js_variant_change:checked, select.js_variant_change').forEach(() => {
            VariantMixin.handleCustomValues(this);
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
    getCustomVariantValues: function (container) {
        const variantCustomValues = [];
        container.querySelectorAll('.variant_custom_value').forEach(() => {
            const variantCustomValueInput = this;
            if (variantCustomValueInput.length !== 0){
                variantCustomValues.push({
                    'custom_product_template_attribute_value_id': variantCustomValueInput.dataset.custom_product_template_attribute_value_id,
                    'attribute_value_name': variantCustomValueInput.dataset.attribute_value_name,
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
    getNoVariantAttributeValues: function (container) {
        const noVariantAttributeValues = [];
        const variantsValuesSelectors = [
            'input.no_variant.js_variant_change:checked',
            'select.no_variant.js_variant_change'
        ];

        container.querySelectorAll(variantsValuesSelectors.join(',')).forEach(() => {
            var variantValueInput = this;
            var singleNoCustom = variantValueInput.dataset.is_single && !variantValueInput.dataset.is_custom;

            if (variantValueInput.tagname === 'SELECT'){
                variantValueInput = variantValueInput.querySelector('option[value=' + variantValueInput.value + ']');
            }

            if (variantValueInput.length !== 0 && !singleNoCustom){
                noVariantAttributeValues.push({
                    'custom_product_template_attribute_value_id': variantValueInput.dataset.value_id,
                    'attribute_value_name': variantValueInput.dataset.value_name,
                    'value': variantValueInput.value,
                    'attribute_name': variantValueInput.dataset.attribute_name,
                    'is_custom': variantValueInput.dataset.is_custom,
                });
            }
        });

        return noVariantAttributeValues;
    },

    /**
     * Will return the list of selected product.template.attribute.value ids
     * For the modal, the "main product"'s attribute values are stored in the
     * "unchanged_value_ids" data
     *
     * @param {Element} container the container to look into
     */
    getSelectedVariantValues: function (container) {
        const values = [];
        const unchangedValues =
            [...container.querySelectorAll('div.oe_unchanged_value_ids')].map((el) => el.dataset.unchangedValueIds) || [];

        const variantsValuesSelectors = [
            'input.js_variant_change:checked',
            'select.js_variant_change'
        ];
        container.querySelectorAll(variantsValuesSelectors.join(', ')).forEach((el) => {
            values.push(+el.value);
        });

        return values.concat(unchangedValues);
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
    selectOrCreateProduct: function (container, productId, productTemplateId) {
        productId = parseInt(productId);
        productTemplateId = parseInt(productTemplateId);
        var productReady = Promise.resolve();
        if (productId) {
            productReady = Promise.resolve(productId);
        } else {
            var params = {
                product_template_id: productTemplateId,
                product_template_attribute_value_ids:
                    JSON.stringify(VariantMixin.getSelectedVariantValues(container)),
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
     * @param {Element} parent the parent container to apply exclusions
     * @param {Array} combination the selected combination of product attribute values
     * @param {Array} parentExclusions the exclusions induced by the variant selection of the parent product
     * For example chair cannot have steel legs if the parent Desk doesn't have steel legs
     */
    _checkExclusions: function (parent, combination, parentExclusions) {
        const self = this;
        const combinationData = parent.querySelectorAll('ul[data-attribute_exclusions]').forEach((el) => el.dataset.attributeExclusions);

        if (parentExclusions && combinationData.parent_exclusions) {
            combinationData.parent_exclusions = parentExclusions;
        }
        let elements = parent.querySelectorAll('option, input, label, .o_variant_pills');
        elements.forEach(el => {
            el.classList.remove('css_not_available');
            el.title = el.dataset.valueName || '';
            el.dataset.excludedBy = '';
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
                            parent,
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
                                parent,
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
                            parent,
                            disabledPtav,
                            ptav,
                            combinationData.mapped_attribute_names,
                        )
                    });
                }
            });
        }

        // parent exclusions (tell which attributes are excluded from parent)
        for (const [excluded_by, exclusions] of Object.entries(
            combinationData.parent_exclusions || {}
        )) {
            // check that the selected combination is in the parent exclusions
            exclusions.forEach((ptav) => {
                // disable the excluded input (even when not already selected)
                // to give a visual feedback before click
                self._disableInput(
                    parent,
                    ptav,
                    excluded_by,
                    combinationData.mapped_attribute_names,
                    combinationData.parent_product_name
                );
            });
        }
    },
    /**
     * Extracted to a method to be extendable by other modules
     *
     * @param {Element} parent
     */
    _getProductId: function (parent) {
        return parseInt(parent.querySelector('.product_id').value);
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
     * @param {Element} parent
     * @param {integer} attributeValueId
     * @param {integer} excludedBy The attribute value that excludes this input
     * @param {Object} attributeNames A dict containing all the names of the attribute values
     *   to show a human readable message explaining why the input is disabled.
     * @param {string} [productName] The parent product. If provided, it will be appended before
     *   the name of the attribute value that excludes this input
     *   e.g: Not available with Customizable Desk (Color: Black)
     */
    _disableInput: function (parent, attributeValueId, excludedBy, attributeNames, productName) {
        const input = parent.querySelector(`option[value='${attributeValueId}'], input[value='${attributeValueId}']`);
        input.classList.add('css_not_available');
        input.closest('label').classList.add('css_not_available');
        input.closest('.o_variant_pills').classList.add('css_not_available');

        if (excludedBy && attributeNames) {
            var target = input.tagName === 'OPTION' ? input : [input.closest('label'), input]
            var excludedByData = [];
            if (target.dataset.excludedBy) {
                excludedByData = JSON.parse(target.dataset.excludedBy);
            }

            var excludedByName = attributeNames[excludedBy];
            if (productName) {
                excludedByName = productName + ' (' + excludedByName + ')';
            }
            excludedByData.push(excludedByName);

            target.attr('title', _t('Not available with %s', excludedByData.join(', ')));
            target.data('excluded-by', JSON.stringify(excludedByData));
        }
    },
    /**
     * @see onChangeVariant
     *
     * @private
     * @param {MouseEvent} ev
     * @param {Element} parent
     * @param {Array} combination
     */
    _onChangeCombination: function (ev, parent, combination) {
        const pricePerUom = parent.querySelector(".o_base_unit_price:first .oe_currency_value");
        if (pricePerUom) {
            if (combination.is_combination_possible !== false && combination.base_unit_price != 0) {
                pricePerUom.closest(".o_base_unit_price_wrapper").classList.remove("d-none");
                pricePerUom.textContent = this._priceToStr(combination.base_unit_price);
                parent.querySelector(".oe_custom_base_unit:first").textContent = combination.base_unit_name;
            } else {
                pricePerUom.closest(".o_base_unit_price_wrapper").classList.add("d-none");
            }
        }

        // Triggers a new JS event with the correct payload, which is then handled
        // by the google analytics tracking code.
        // Indeed, every time another variant is selected, a new view_item event
        // needs to be tracked by google analytics.
        if ('product_tracking_info' in combination) {
            const product = document.getElementById('product_detail');
            product.dataset.productTrackingInfo = combination['product_tracking_info'];
            product.dispatchEvent(new CustomEvent('view_item_event', { detail: combination['product_tracking_info'] }));
        }
        const addToCart = parent.querySelector('#add_to_cart_wrap');
        const contactUsButton = parent.querySelector('#contact_us_wrapper');
        const productPrice = parent.querySelector('.product_price');
        const quantity = parent.querySelector('.css_quantity');
        const product_unavailable = parent.querySelector('#product_unavailable');
        if (combination.prevent_zero_price_sale) {
            productPrice.classList.remove('d-inline-block');
            productPrice.classList.add('d-none');

            quantity.classList.remove('d-inline-flex');
            quantity.classList.add('d-none');

            addToCart.classList.remove('d-inline-flex');
            addToCart.classList.add('d-none');

            contactUsButton.classList.remove('d-none');
            contactUsButton.classList.add('d-flex');

            product_unavailable.classList.remove('d-none');
            product_unavailable.classList.add('d-flex');
        } else {
            productPrice.classList.remove('d-none');
            productPrice.classList.add('d-inline-block');

            quantity.classList.remove('d-none');
            quantity.classList.add('d-inline-flex');

            addToCart.classList.remove('d-none');
            addToCart.classList.add('d-inline-flex');

            contactUsButton.classList.remove('d-flex');
            contactUsButton.classList.add('d-none');

            product_unavailable.classList.remove('d-flex');
            product_unavailable.classList.add('d-none');
        }

        const self = this;
        const price = parent.querySelector(".oe_price .oe_currency_value");
        const default_price = parent.querySelector(".oe_default_price .oe_currency_value");
        const optional_price = parent.querySelector(".oe_optional .oe_currency_value");

        price.textContent = self._priceToStr(combination.price);
        default_price.textContent = self._priceToStr(combination.list_price);

        var isCombinationPossible = true;
        if (typeof combination.is_combination_possible !== "undefined") {
            isCombinationPossible = combination.is_combination_possible;
        }
        this._toggleDisable(parent, isCombinationPossible);

        if (combination.has_discounted_price && !combination.compare_list_price) {
            default_price.closest('.oe_website_sale').classList.add("discount");
            optional_price.closest('.oe_optional').classList.remove('d-none').style.textDecoration = 'line-through';
            default_price.parentElement.classList.remove('d-none');
        } else {
            default_price.closest('.oe_website_sale').classList.remove("discount");
            optional_price.closest('.oe_optional').classList.add('d-none');
            default_price.parentElement.classList.add('d-none');
        }

        var rootComponentSelectors = [
            'tr.js_product',
            '.oe_website_sale',
            '.o_product_configurator'
        ];

        // update images only when changing product
        // or when either ids are 'false', meaning dynamic products.
        // Dynamic products don't have images BUT they may have invalid
        // combinations that need to disable the image.
        if (!combination.product_id ||
            !this.last_product_id ||
            combination.product_id !== this.last_product_id) {
            this.last_product_id = combination.product_id;
            self._updateProductImage(
                parent.closest(rootComponentSelectors.join(', ')),
                combination.display_image,
                combination.product_id,
                combination.product_template_id,
                combination.carousel,
                isCombinationPossible
            );
        }

        let productIdElement = parent.querySelector('.product_id');
        productIdElement.value = combination.product_id || 0;
        productIdElement.dispatchEvent(new Event('change'));

        let productDisplayNameElement = parent.querySelector('.product_display_name');
        productDisplayNameElement.textContent = combination.display_name;

        let rawPriceElement = parent.querySelector('.js_raw_price');
        rawPriceElement.textContent = combination.price;
        rawPriceElement.dispatchEvent(new Event('change'));

        let productTagsElement = parent.querySelector('.o_product_tags');
        productTagsElement.innerHTML = combination.product_tags;

        this.handleCustomValues(ev.target);
    },

    /**
     * returns the formatted price
     *
     * @private
     * @param {float} price
     */
    _priceToStr: function (price) {
        let precision = 2;

        const precisionEls = this.el.querySelectorAll('.decimal_precision');
        const lastElement = precisionEls[precisionEls - 1];
        if (precisionEls.length) {
            precision = parseInt(lastElement.dataset.precision);
        }
        var formatted = price.toFixed(precision).split(".");
        const { thousandsSep, decimalPoint, grouping } = localization;
        formatted[0] = insertThousandsSep(formatted[0], thousandsSep, grouping);
        return formatted.join(decimalPoint);
    },
    /**
     * Returns a throttled `_getCombinationInfo` with a leading and a trailing
     * call, which is memoized per `uniqueId`, and for which previous results
     * are dropped.
     *
     * The uniqueId is needed because on the configurator modal there might be
     * multiple elements triggering the rpc at the same time, and we need each
     * individual product rpc to be executed, but only once per individual
     * product.
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
     * @param {Element} parent
     * @param {boolean} isCombinationPossible
     */
    _toggleDisable: function (parent, isCombinationPossible) {
        if (parent.classList.contains('in_cart')) {
            const secondaryButton = parent.closest('.modal-content').querySelector('.modal-footer .btn-secondary');
            secondaryButton.disabled = !isCombinationPossible;
            secondaryButton.classList.toggle('disabled', !isCombinationPossible);
        }
        parent.classList.toggle('css_not_available', !isCombinationPossible);
        if (parent.classList.contains('in_cart')) {
            const primaryButton = parent.closest('.modal-content').querySelector('.modal-footer .btn-primary');
            primaryButton.disabled = !isCombinationPossible;
            primaryButton.classList.toggle('disabled', !isCombinationPossible);
        }
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
    _updateProductImage: function (productContainer, displayImage, productId, productTemplateId) {
        const model = productId ? 'product.product' : 'product.template';
        const modelId = productId || productTemplateId;
        const imageUrl = '/web/image/{0}/{1}/' + (this._productImageField ? this._productImageField : 'image_1024');
        const imageSrc = imageUrl
            .replace("{0}", model)
            .replace("{1}", modelId);

        const imagesSelectors = [
            'span[data-oe-model^="product."][data-oe-type="image"] img:first',
            'img.product_detail_img',
            'span.variant_image img',
            'img.variant_image',
        ];

        const img = productContainer.querySelector(imagesSelectors.join(', '));

        if (displayImage) {
            img.classList.remove('invisible')
            img.setAttribute('src', imageSrc);
        } else {
            img.classList.add('invisible');
        }
    },

    /**
     * Highlight selected color
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onChangeColorAttribute: function (ev) {
        const parent = ev.target.closest('.js_product');
        const colorElements = parent.querySelectorAll('.css_attribute_color');
        colorElements.forEach(el => {
            el.classList.remove('active');
            if (el.querySelector('input:checked')) {
                el.classList.add('active');
            }
        });
    },

    _onChangePillsAttribute: function (ev) {
        const parent = ev.target.closest('.js_product');
        const variantPillEls = parent.querySelectorAll('.o_variant_pills');
        variantPillEls.forEach(el => {
            el.classList.remove('active');
            if (el.querySelector('input:checked')) {
                el.classList.add('active');
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
