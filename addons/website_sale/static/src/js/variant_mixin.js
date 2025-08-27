import { localization } from '@web/core/l10n/localization';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { KeepLast } from '@web/core/utils/concurrency';
import { memoize } from '@web/core/utils/functions';
import { insertThousandsSep } from '@web/core/utils/numbers';
import { throttleForAnimation } from '@web/core/utils/timing';
import { markup } from '@odoo/owl';
import wSaleUtils from '@website_sale/js/website_sale_utils';

const VariantMixin = {
    /**
     * @see onChangeVariant
     *
     * @private
     * @param {Event} ev
     * @returns {Deferred}
     */
    async _getCombinationInfo(ev) {
        if (ev.target.classList.contains('variant_custom_value')) return Promise.resolve();
        const parent = ev.target.closest('.js_product');
        if (!parent) return Promise.resolve();
        const combination = wSaleUtils.getSelectedAttributeValues(parent);

        const combinationInfo = await this.waitFor(rpc('/website_sale/get_combination_info', {
            'product_template_id': parseInt(parent.querySelector('.product_template_id')?.value),
            'product_id': this._getProductId(parent),
            'combination': combination,
            'add_qty': parseInt(parent.querySelector('input[name="add_qty"]')?.value),
            'uom_id': this._getUoMId(parent),
            'context': this.context,
            ...this._getOptionalCombinationInfoParam(parent),
        }));
        this._onChangeCombination(ev, parent, combinationInfo);
        this._checkExclusions(parent, combination);
    },

    _getUoMId(element) {
        return parseInt(element.querySelector('input[name="uom_id"]:checked')?.value)
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
     * @param {Element} el
     */
    handleCustomValues(el) {
        let variantContainer;
        let customInput = false;
        if (el.matches('input[type=radio]:checked')) {
            variantContainer = el.closest('ul').closest('li');
            customInput = el;
        } else if (el.matches('select')) {
            variantContainer = el.closest('li');
            customInput = el.querySelector(`option[value="${el.value}"]`);
        }

        if (variantContainer) {
            const customValue = variantContainer.querySelector('.variant_custom_value');
            if (customInput && customInput.dataset.isCustom === 'True') {
                const attributeValueId = customInput.dataset.valueId;
                if (
                    !customValue
                    || customValue.dataset.customProductTemplateAttributeValueId !== attributeValueId
                ) {
                    customValue?.remove();

                    const previousCustomValue = customInput.getAttribute('previous_custom_value');
                    const input = document.createElement('input');
                    input.type = 'text';
                    input.dataset.customProductTemplateAttributeValueId = attributeValueId;
                    input.classList.add(
                        'variant_custom_value', 'custom_value_radio', 'form-control', 'mt-2'
                    );
                    input.setAttribute('placeholder', customInput.dataset.valueName);
                    variantContainer.appendChild(input);
                    if (previousCustomValue) {
                        input.value = previousCustomValue;
                    }
                }
            } else {
                customValue?.remove();
            }
        }
    },

    /**
     * Triggers the price computation and other variant specific changes
     *
     * @param {Element} container
     */
    triggerVariantChange(container) {
        container.querySelectorAll('ul[data-attribute-exclusions]')
            .forEach((el) => el.dispatchEvent(new Event('change')));
        container.querySelectorAll('input.js_variant_change:checked, select.js_variant_change')
            .forEach((el) => this.handleCustomValues(el));
    },

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
     */
    _checkExclusions(parent, combination) {
        const combinationDataJson = parent.querySelector('ul[data-attribute-exclusions]')
            .dataset.attributeExclusions;
        const combinationData = combinationDataJson ? JSON.parse(combinationDataJson) : {};

        parent.querySelectorAll('option, input, label, .o_variant_pills').forEach(el => {
            el.classList.remove('css_not_available');
        });
        parent.querySelectorAll('option, input').forEach(el => {
            const li = el.closest('li');
            if (li) {
                li.removeAttribute('title');
                li.dataset.excludedBy = '';
            }
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
                        this._disableInput(
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
        // for example a product with 3 attributes of which 1 combination is unavailable (archived)
        // requires the first 2 to be selected for the third to be grayed out
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
                            this._disableInput(
                                parent,
                                ptav,
                                ptavOther,
                                combinationData.mapped_attribute_names,
                            );
                        });
                    });
                } else if (
                    !!ptavCommon
                    && (combination.length === excludedCombination.length)
                    && (ptavCommon.length === (combination.length - 1))
                ) {
                    // In this case we only need to disable the remaining ptav
                    const unavailablePtav = excludedCombination.find(
                        (ptav) => !combination.includes(ptav)
                    );
                    excludedCombination.forEach((ptav) => {
                        if (ptav === unavailablePtav) {
                            return;
                        }
                        this._disableInput(
                            parent,
                            unavailablePtav,
                            ptav,
                            combinationData.mapped_attribute_names,
                        );
                    });
                }
            });
        }
    },

    /**
     * Extracted to a method to be extendable by other modules
     *
     * @param {Element} parent
     */
    _getProductId(parent) {
        return parseInt(parent.querySelector('.product_id').value);
    },

    /**
     * Will gray out the input/option that refers to the passed attributeValueId.
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
     *   to show a human readable message explaining why the input is grayed out.
     * @param {string} [productName] The parent product. If provided, it will be appended before
     *   the name of the attribute value that excludes this input
     *   e.g: Not available with Customizable Desk (Color: Black)
     */
    _disableInput(parent, attributeValueId, excludedBy, attributeNames, productName) {
        const input = parent.querySelector(
            `option[value="${attributeValueId}"], input[value="${attributeValueId}"]`
        );
        input.classList.add('css_not_available')
        input.closest('label')?.classList?.add('css_not_available');
        input.closest('.o_variant_pills')?.classList?.add('css_not_available');

        const li = input.closest('li');

        if (li && excludedBy && attributeNames) {
            const excludedByData = li.dataset.excludedBy ? li.dataset.excludedBy.split(',') : [];

            let excludedByName = attributeNames[excludedBy];
            if (productName) {
                excludedByName = `${productName} (${excludedByName})`;
            }
            excludedByData.push(excludedByName);

            li.setAttribute('title', _t("Not available with %s", excludedByData.join(', ')));
            li.dataset.excludedBy = excludedByData.join(',');
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
    _onChangeCombination(ev, parent, combination) {
        const isCombinationPossible = !!combination.is_combination_possible;
        const precision = combination.currency_precision;
        const productPrice = parent.querySelector('.product_price');
        if (productPrice && !productPrice.classList.contains('decimal_precision')) {
            productPrice.classList.add('decimal_precision');
            productPrice.dataset.precision = precision;
        }
        const pricePerUom = parent.querySelector('.o_base_unit_price')
            ?.querySelector('.oe_currency_value');
        if (pricePerUom) {
            const hasPrice = isCombinationPossible && combination.base_unit_price !== 0;
            pricePerUom.closest('.o_base_unit_price_wrapper').classList.toggle('d-none', !hasPrice);
            if (hasPrice) {
                pricePerUom.textContent = this._priceToStr(combination.base_unit_price, precision);
                const unit = parent.querySelector('.oe_custom_base_unit');
                if (unit) {
                    unit.textContent = combination.base_unit_name;
                }
            }
        }

        // Triggers a new JS event with the correct payload, which is then handled
        // by the google analytics tracking code.
        // Indeed, every time another variant is selected, a new view_item event
        // needs to be tracked by google analytics.
        if ('product_tracking_info' in combination) {
            const product = document.querySelector('#product_detail');
            product.dispatchEvent(
                new CustomEvent('view_item_event', { 'detail': combination['product_tracking_info'] })
            );
        }
        const addToCart = parent.querySelector('#add_to_cart_wrap');
        const contactUsButton = parent.closest('#product_details')
            ?.querySelector('#contact_us_wrapper');
        const quantity = parent.querySelector('.css_quantity');
        const productUnavailable = parent.querySelector('#product_unavailable');

        const preventSale = combination.prevent_zero_price_sale;
        productPrice?.classList?.toggle('d-inline-block', !preventSale);
        productPrice?.classList?.toggle('d-none', preventSale);
        quantity?.classList?.toggle('d-inline-flex', !preventSale);
        quantity?.classList?.toggle('d-none', preventSale);
        addToCart?.classList?.toggle('d-inline-flex', !preventSale);
        addToCart?.classList?.toggle('d-none', preventSale);
        contactUsButton?.classList?.toggle('d-none', !preventSale);
        contactUsButton?.classList?.toggle('d-flex', preventSale);
        productUnavailable?.classList?.toggle('d-none', !preventSale);
        productUnavailable?.classList?.toggle('d-flex', preventSale);

        if (contactUsButton) {
            const contactUsButtonLink = contactUsButton.querySelector('a');
            const url = contactUsButtonLink.getAttribute('data-url');
            contactUsButtonLink.setAttribute('href', `${url}?subject=${combination.display_name}`);
        }

        const price = parent.querySelector('.oe_price')?.querySelector('.oe_currency_value');
        const defaultPrice = parent.querySelector('.oe_default_price')
            ?.querySelector('.oe_currency_value');
        const comparePrice = parent.querySelector('.oe_compare_list_price');
        if (price) {
            price.textContent = this._priceToStr(combination.price, precision);
        }
        if (defaultPrice) {
            defaultPrice.textContent = this._priceToStr(combination.list_price, precision);
            defaultPrice.closest('.oe_website_sale').classList
                .toggle('discount', combination.has_discounted_price);
            defaultPrice.parentElement.classList
                .toggle('d-none', !combination.has_discounted_price);
        }
        if (comparePrice) {
            comparePrice.classList.toggle('d-none', combination.has_discounted_price);
        }

        this._toggleDisable(parent, isCombinationPossible);

        // update images & tags only when changing product
        // or when either ids are 'false', meaning dynamic products.
        // Dynamic products don't have images BUT they may have invalid
        // combinations that need to disable the image.
        if (!combination.no_product_change) {
            this._updateProductImage(
                parent.closest('tr.js_product, .oe_website_sale'), combination.carousel
            );
            const productTags = parent.querySelector('.o_product_tags');
            productTags?.insertAdjacentHTML('beforebegin', markup(combination.product_tags));
            productTags?.remove();
        }

        const productIdInput = parent.querySelector('.product_id');
        productIdInput.value = combination.product_id || 0;
        productIdInput.dispatchEvent(new Event('change', { bubbles: true }));

        this.handleCustomValues(ev.target);
    },

    /**
     * returns the formatted price
     *
     * @private
     * @param {float} price
     * @param {integer} precision
     * @returns {string}
     */
    _priceToStr: function (price, precision) {
        if (!Number.isInteger(precision)) {
            precision = parseInt(
                this.el.querySelector('.decimal_precision:last-of-type')?.dataset.precision ?? 2
            );
        }
        const formatted = price.toFixed(precision).split('.');
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
        const _getCombinationInfo = throttleForAnimation(self._getCombinationInfo.bind(self));
        return (ev, params) => keepLast.add(_getCombinationInfo(ev, params));
    }),
};

export default VariantMixin;
