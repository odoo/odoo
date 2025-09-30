import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { localization } from '@web/core/l10n/localization';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { url } from '@web/core/utils/urls';
import { memoize, uniqueId } from '@web/core/utils/functions';
import { KeepLast } from '@web/core/utils/concurrency';
import { insertThousandsSep } from '@web/core/utils/numbers';
import { throttleForAnimation } from '@web/core/utils/timing';
import { markup } from '@odoo/owl';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import { ProductImageViewer } from '@website_sale/js/components/website_sale_image_viewer';

export class ProductPage extends Interaction {
    static selector = '.o_wsale_product_page';
    dynamicContent = {
        '.js_main_product input[name="add_qty"]': { 't-on-change': this.onChangeAddQuantity },
        'a.js_add_cart_json': { 't-on-click.prevent': this.incOrDecQuantity },
        '.o_wsale_product_page_variants': { 't-on-change': this.onChangeVariant },
        '.o_product_page_reviews_link': { 't-on-click': this.onClickReviewsLink },
        '.css_attribute_color input': { 't-on-change': this.onChangeColorAttribute },
        'label[name="o_wsale_attribute_image_selector"] input': {
            't-on-change': this.onChangeImageAttribute,
        },
        '.o_variant_pills': { 't-on-click': this.onChangePillsAttribute },
    };

    start() {
        this._applySearchParams();
        this._triggerVariantChange(this.el);
        this._startZoom();
        // Triggered when selecting a product variant in a carousel.
        window.addEventListener('hashchange', ev => {
            this._applySearchParams();
            this._triggerVariantChange(this.el);
        });
    }

    destroy() {
        this._cleanupZoom();
    }

    /**
     * Mark the variant as changed to recompute the price (which might vary based on the quantity).
     *
     * @param {MouseEvent} ev
     */
    onChangeAddQuantity(ev) {
        const parent = wSaleUtils.getClosestProductForm(ev.currentTarget);
        if (parent) this._triggerVariantChange(parent);
    }

    /**
     * Increase or decrease the quantity based on which button was clicked.
     *
     * @param {MouseEvent} ev
     */
    incOrDecQuantity(ev) {
        const input = ev.currentTarget.closest('.input-group').querySelector('input');
        const min = parseFloat(input.dataset.min || 0);
        const max = parseFloat(input.dataset.max || Infinity);
        const previousQty = parseFloat(input.value || 0);
        const quantity = (
            ev.currentTarget.name === 'remove_one' ? -1 : 1
        ) + previousQty;
        const newQty = quantity > min ? (quantity < max ? quantity : max) : min;

        if (newQty !== previousQty) {
            input.value = newQty;
            // Trigger `onChangeAddQuantity`.
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    /**
     * When the variant is changed, this method will recompute:
     * - Whether the selected combination is possible,
     * - The extra price, if applicable,
     * - The total price,
     * - The display name of the product (e.g. "Customizable desk (White, Steel)"),
     * - Whether a "custom value" input should be shown,
     *
     * "Custom value" changes are ignored since they don't change the combination.
     *
     * @param {MouseEvent} ev
     */
    onChangeVariant(ev) {
        // Write the properties of the form elements in the DOM to prevent the current selection
        // from being lost when activating the web editor.
        const parent = ev.currentTarget.closest('.js_product');
        parent.querySelectorAll('input').forEach(
            el => el.checked ? el.setAttribute('checked', true) : el.removeAttribute('checked')
        );
        parent.querySelectorAll('select option').forEach(
            el => el.selected ? el.setAttribute('selected', true) : el.removeAttribute('selected')
        );

        this._setSearchParams();

        if (!parent.dataset.uniqueId) {
            parent.dataset.uniqueId = uniqueId();
        }
        this._throttledGetCombinationInfo(parent.dataset.uniqueId)(ev);
    }

    /**
     * Uncollapse the reviews.
     */
    onClickReviewsLink() {
        window.Collapse.getOrCreateInstance(
            document.querySelector('#o_product_page_reviews_content')
        ).show();
    }

    /**
     * Highlight the selected color.
     *
     * @param {MouseEvent} ev
     */
    onChangeColorAttribute(ev) {
        const eventTarget = ev.target;
        const parent = eventTarget.closest('.js_product');
        parent.querySelectorAll('.css_attribute_color').forEach(
            el => el.classList.toggle('active', el.matches(':has(input:checked)'))
        );
        const attrValueEl = eventTarget.closest('.variant_attribute')
            ?.querySelector('.attribute_value');
        if (attrValueEl) {
            attrValueEl.innerText = eventTarget.dataset.valueName;
        }
    }

    /**
     * Highlight the selected image.
     *
     * @param {MouseEvent} ev
     */
    onChangeImageAttribute(ev) {
        const parent = ev.target.closest('.js_product');
        const images = parent.querySelectorAll('label[name="o_wsale_attribute_image_selector"]');
        images.forEach(el => el.classList.remove('active'));
        images.forEach(el => {
            const input = el.querySelector('input');
            if (input && input.checked) {
                el.classList.add('active');
            }
        });
        const attrValueEl = ev.target
            .closest('[name="variant_attribute"]')?.querySelector('[name="attribute_value"]');
        if (attrValueEl) {
            attrValueEl.innerText = ev.target.dataset.valueName;
        }
    }

    /**
     * Highlight the selected pill.
     *
     * @param {MouseEvent} ev
     */
    onChangePillsAttribute(ev) {
        const radio = ev.target.closest('.o_variant_pills').querySelector('input');
        radio.click(); // Trigger `onChangeVariant`.
        const parent = ev.target.closest('.js_product');
        parent.querySelectorAll('.o_variant_pills').forEach(el => {
            if (el.matches(':has(input:checked)')) {
                el.classList.add(
                    'active', 'border-primary', 'text-primary-emphasis', 'bg-primary-subtle'
                );
            } else {
                el.classList.remove(
                    'active', 'border-primary', 'text-primary-emphasis', 'bg-primary-subtle'
                );
            }
        });
    }

    /**
     * Set the selected attribute values based on the URL search params.
     */
    _applySearchParams() {
        let params = new URLSearchParams(window.location.search);
        let attributeValues = params.get('attribute_values')
        if (!attributeValues) {
            // TODO remove in 20 (or later): hash support of attribute values
            params = new URLSearchParams(window.location.hash.substring(1));
            attributeValues = params.get('attribute_values')
        }
        if (attributeValues) {
            const attributeValueIds = attributeValues.split(',');
            const inputs = document.querySelectorAll(
                'input.js_variant_change, select.js_variant_change option'
            );
            let combinationChanged = false;
            inputs.forEach(element => {
                if (attributeValueIds.includes(element.dataset.attributeValueId)) {
                    if (element.tagName === 'INPUT' && !element.checked) {
                        element.checked = true;
                        combinationChanged = true;
                    } else if (element.tagName === 'OPTION' && !element.selected) {
                        element.selected = true;
                        combinationChanged = true;
                    }
                }
            });
            if (combinationChanged) {
                this._changeAttribute(
                    '.css_attribute_color, [name="o_wsale_attribute_image_selector"], .o_variant_pills'
                );
            }
        }
    }

    /**
     * Set the URL search params based on the selected attribute values.
     */
    _setSearchParams() {
        const inputs = document.querySelectorAll(
            'input.js_variant_change:checked, select.js_variant_change option:checked'
        );
        const attributeIds = Array.from(inputs).map(el => el.dataset.attributeValueId);
        if (attributeIds.length) {
            const params = new URLSearchParams(window.location.search);
            params.set('attribute_values', attributeIds.join(','))
            // Avoid adding new entries in session history by replacing the current one
            history.replaceState(
                null, '', url(window.location.pathname, Object.fromEntries(params))
            );
        }
    }

    /**
     * Set the checked values active.
     *
     * @param {String} selector - The selector matching the attributes to change.
     */
    _changeAttribute(selector) {
        this.el.querySelectorAll(selector).forEach(el => {
            const input = el.querySelector('input');
            const isActive = input?.checked;
            el.classList.toggle('active', isActive);
            if (isActive) input.dispatchEvent(new Event('change', { bubbles: true }));
        });
    }

    _getProductImageContainerSelector() {
        const imageLayout = this.el.querySelector('#product_detail_main').dataset.imageLayout;
        return {
            'carousel': '#o-carousel-product',
            'grid': '#o-grid-product',
        }[imageLayout];
    }

    _startZoom() {
        this._cleanupZoom();
        this.zoomCleanup = [];
        // Zoom on click
        if (this.el.dataset.ecomZoomClick) {
            // In this case we want all the images not just the ones that are "zoomables"
            const images = this.el.querySelectorAll('.product_detail_img');
            const { imageRatio, imageRatioMobile } = this.el.dataset;
            for (const [idx, image] of images.entries()) {
                const handler = () =>
                    this.services.dialog.add(ProductImageViewer, {
                        selectedImageIdx: idx,
                        images,
                        imageRatio,
                        imageRatioMobile,
                    });
                image.addEventListener("click", handler);
                this.zoomCleanup.push(() => image.removeEventListener("click", handler));
            }
        }
    }

    _cleanupZoom() {
        if (!this.zoomCleanup || !this.zoomCleanup.length) return;
        for (const cleanup of this.zoomCleanup) {
            cleanup();
        }
        this.zoomCleanup = undefined;
    }

    /**
     * Update the product images.
     */
    _updateProductImages(productContainer, newImages) {
        let images = productContainer.querySelector(this._getProductImageContainerSelector());
        const isEditorEnabled = document.body.classList.contains('editor_enable');
        // Don't update the images when using the web editor. Otherwise, the images may not be
        // editable (depending on whether the images are updated before or after the editor is
        // ready).
        if (images && !isEditorEnabled) {
            images.insertAdjacentHTML('beforebegin', markup(newImages));
            images.remove();

            // Re-query the latest images.
            images = productContainer.querySelector(this._getProductImageContainerSelector());
            // Update the sharable image (only works for Pinterest).
            const shareImageSrc = images.querySelector('img').src;
            document.querySelector('meta[property="og:image"]')
                .setAttribute('content', shareImageSrc);

            if (images.id === 'o-carousel-product') {
                window.Carousel.getOrCreateInstance(images).to(0);
            }
            this._startZoom();
        }
    }

    /**
     * Toggles the disabled class on the parent element and the "add to cart" and "buy now" buttons
     * depending on whether the current combination is possible.
     *
     * @param {Element} parent
     * @param {boolean} isCombinationPossible
     */
    _toggleDisable(parent, isCombinationPossible) {
        parent.classList.toggle('css_not_available', !isCombinationPossible);
        parent.querySelector('#add_to_cart')?.classList?.toggle('disabled', !isCombinationPossible);
        parent.querySelector('.o_we_buy_now')?.classList?.toggle('disabled', !isCombinationPossible);
    }

    /**
     * @see onChangeVariant
     *
     * @param {Event} ev
     */
    async _getCombinationInfo(ev) {
        if (ev.target.classList.contains('variant_custom_value')) return Promise.resolve();
        const parent = ev.target.closest('.js_product');
        if (!parent) return Promise.resolve();
        const combination = wSaleUtils.getSelectedAttributeValues(parent);

        const combinationInfo = await this.waitFor(rpc('/website_sale/get_combination_info', {
            'product_template_id': parseInt(parent.querySelector('.product_template_id')?.value),
            'product_id': parseInt(parent.querySelector('.product_id')?.value),
            'combination': combination,
            'add_qty': parseInt(parent.querySelector('input[name="add_qty"]')?.value),
            'uom_id': this._getUoMId(parent),
            'context': this.context,
            ...this._getOptionalCombinationInfoParams(parent),
        }));
        this._onChangeCombination(ev, parent, combinationInfo);
        this._checkExclusions(parent, combination);
    }

    _getUoMId(element) {
        return parseInt(element.querySelector('input[name="uom_id"]:checked')?.value)
    }

    /**
     * Hook to add optional params to the `get_combination_info` RPC.
     *
     * @param {Element} product
     */
    _getOptionalCombinationInfoParams(product) {
        return {};
    }

    /**
     * Add a "custom value" input for this attribute value iff the attribute value is configured as
     * "custom".
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
                    const customValueInput = document.createElement('input');
                    customValueInput.type = 'text';
                    customValueInput.dataset.customProductTemplateAttributeValueId = attributeValueId;
                    customValueInput.classList.add(
                        'variant_custom_value', 'custom_value_radio', 'form-control', 'mt-2'
                    );
                    customValueInput.setAttribute('placeholder', customInput.dataset.valueName);
                    variantContainer.appendChild(customValueInput);
                    if (previousCustomValue) {
                        customValueInput.value = previousCustomValue;
                    }
                }
            } else {
                customValue?.remove();
            }
        }
    }

    /**
     * Trigger the price computation and other variant specific changes.
     *
     * @param {Element} container
     */
    _triggerVariantChange(container) {
        container.querySelectorAll('.o_wsale_product_page_variants').forEach(
            el => el.dispatchEvent(new Event('change')) // Trigger `onChangeVariant`.
        );
        container.querySelectorAll('input.js_variant_change:checked, select.js_variant_change').forEach(
            el => this.handleCustomValues(el)
        );
    }

    /**
     * Disable the attribute value inputs based on combination exclusions and disable the "add to
     * cart" button if the selected combination is not available.
     *
     * This method will check both the exclusions within the product itself and the exclusions
     * coming from the parent product (meaning that this product is an option of the parent
     * product).
     *
     * This method will also check that the selected combination does not match a manually archived
     * product.
     *
     * @param {Element} parent - The parent container to apply exclusions.
     * @param {Array} combination - The selected combination of product attribute values.
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
        if (combinationData.exclusions) {
            // Browse all selected PTAVs.
            Object.values(combination).forEach(selectedPtav => {
                if (combinationData.exclusions.hasOwnProperty(selectedPtav)) {
                    // For each exclusion of the selected PTAV, disable the excluded PTAV (even if
                    // unselected) to provide visual feedback.
                    Object.values(combinationData.exclusions[selectedPtav]).forEach(
                        excludedPtav => this._disableInput(
                            parent,
                            excludedPtav,
                            selectedPtav,
                            combinationData.mapped_attribute_names,
                        )
                    );
                }
            });
        }
        if (combinationData.archived_combinations) {
            combinationData.archived_combinations.forEach(excludedCombination => {
                const commonPtavs = excludedCombination.filter(ptav => combination.includes(ptav));
                if (
                    !!commonPtavs
                    && combination.length === excludedCombination.length
                    && commonPtavs.length === combination.length
                ) {
                    // The selected combination is archived. All selected PTAVs must be disabled.
                    combination.forEach(ptav => combination.forEach(otherPtav => {
                        if (ptav === otherPtav) return;
                        this._disableInput(
                            parent, ptav, otherPtav, combinationData.mapped_attribute_names
                        );
                    }));
                } else if (
                    !!commonPtavs
                    && combination.length === excludedCombination.length
                    && commonPtavs.length === combination.length - 1
                ) {
                    // The selected combination has all but one PTAV in common with the archived
                    // combination. The single unselected PTAV from the archived combination must be
                    // disabled.
                    const unavailablePtav = excludedCombination.find(
                        ptav => !combination.includes(ptav)
                    );
                    excludedCombination.forEach(ptav => {
                        if (ptav === unavailablePtav) return;
                        this._disableInput(
                            parent, unavailablePtav, ptav, combinationData.mapped_attribute_names
                        );
                    });
                }
            });
        }
    }

    /**
     * Gray out the input/option that refers to the provided attributeValueId to show the user that
     * some combinations are not available.
     *
     * This method will also display a message explaining why the input is not selectable based on
     * the "excludedBy" and the "productName" params. E.g. "Not available with Color: Gray".
     *
     * @param {Element} parent
     * @param {integer} attributeValueId
     * @param {integer} excludedBy - The attribute value that excludes this one.
     * @param {Object} attributeNames - A dict containing all the names of the attribute values
     *     to show a human-readable message explaining why the input is grayed out.
     * @param {string} [productName] - The parent product. If provided, it will be appended before
     *     the name of the attribute value that excludes this one. E.g. "Not available with
     *     Customizable Desk (Color: Gray)".
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
    }

    /**
     * @see onChangeVariant
     *
     * @param {Event} ev
     * @param {Element} parent
     * @param {Object} combination
     */
    async _onChangeCombination(ev, parent, combination) {
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

        if ('product_tracking_info' in combination) {
            const product = document.querySelector('#product_detail');
            // Trigger an event to track variant changes in Google Analytics.
            product.dispatchEvent(new CustomEvent(
                'view_item_event', { 'detail': combination['product_tracking_info'] }
            ));
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

        // Only update the images and tags if the product has changed.
        if (!combination.no_product_change) {
            this._updateProductImages(
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
    }

    /**
     * Return the formatted price.
     *
     * @param {float} price - The price to format.
     * @param {integer} precision - Number of decimals to display.
     * @return {string} - The formatted price.
     */
    _priceToStr(price, precision) {
        if (!Number.isInteger(precision)) {
            precision = parseInt(
                this.el.querySelector('.decimal_precision:last-of-type')?.dataset.precision ?? 2
            );
        }
        const formatted = price.toFixed(precision).split('.');
        const { thousandsSep, decimalPoint, grouping } = localization;
        formatted[0] = insertThousandsSep(formatted[0], thousandsSep, grouping);
        return formatted.join(decimalPoint);
    }

    /**
     * Return a throttled `_getCombinationInfo` with a leading and a trailing call, which is
     * memoized per `uniqueId`, and for which previous results are dropped.
     *
     * `uniqueId` is needed because there might be multiple elements triggering the RPC at the same
     * time, and we need each individual RPC to be executed, but only once per product.
     *
     * The leading call is needed to keep good reactivity on the first call, for a better user
     * experience. The trailing call is because ultimately only the information about the last
     * selected combination is useful. All intermediary RPCs can be ignored and are therefore best
     * not done at all.
     *
     * `KeepLast` is needed to make sure we only consider the result of the last call, when several
     * (asynchronous) calls are done in parallel.
     *
     * @param {string} uniqueId
     * @return {function}
     */
    _throttledGetCombinationInfo = memoize(uniqueId => {
        const keepLast = new KeepLast();
        const getCombinationInfo = throttleForAnimation(this._getCombinationInfo.bind(this));
        return (ev, params) => keepLast.add(getCombinationInfo(ev, params));
    });
}

registry.category('public.interactions').add('website_sale.product_page', ProductPage);
