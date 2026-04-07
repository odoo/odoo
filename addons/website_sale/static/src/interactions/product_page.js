import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { router } from '@web/core/browser/router';
import { localization } from '@web/core/l10n/localization';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { url } from '@web/core/utils/urls';
import { memoize, uniqueId } from '@web/core/utils/functions';
import { KeepLast } from '@web/core/utils/concurrency';
import { setElementContent } from '@web/core/utils/html';
import { insertThousandsSep, formatFloat } from '@web/core/utils/numbers';
import { renderToElement, renderToFragment } from '@web/core/utils/render';
import { isEmail } from '@web/core/utils/strings';
import { throttleForAnimation } from '@web/core/utils/timing';
import { htmlEscape, markup } from '@odoo/owl';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import { ProductImageViewer } from '@website_sale/js/components/website_sale_image_viewer';

export class ProductPage extends Interaction {
    static selector = '.o_wsale_product_page';
    dynamicContent = {
        '.js_product input[name="add_qty"]': { 't-on-change': this.onChangeAddQuantity },
        '.css_quantity > button': { 't-on-click.prevent': this.incOrDecQuantity },
        '.o_wsale_product_page_variants': { 't-on-change': this.onChangeVariant },
        '.o_product_page_reviews_link': { 't-on-click': this.onClickReviewsLink },
        'label[name="o_wsale_attribute_color_selector"] input': {
            't-on-change': this.onChangeAttribute
        },
        'label[name="o_wsale_attribute_image_selector"] input': {
            't-on-change': this.onChangeAttribute
        },
        'label[name="o_wsale_attribute_thumbnail_selector"] input': {
            't-on-change': this.onChangeAttribute
        },
        '.o_variant_pills': { 't-on-click': this.onChangePillsAttribute },
        ".o_packaging_button": {
            "t-on-mouseenter": this.onHoverPackagingButton,
            "t-on-mouseleave": this.onMouseLeavePackagingButton,
            "t-on-click": this.onMouseLeavePackagingButton,
        },
        "#product_stock_notification_message": {
            "t-on-click": this.onClickProductStockNotificationMessage.bind(this),
        },
        "#product_stock_notification_form_submit_button": {
            "t-on-click": this.onClickSubmitProductStockNotificationForm.bind(this),
        },
        "button[name='add_to_cart']": {
            "t-on-product_added_to_cart": this._getCombinationInfo.bind(this),
        },
        "#wishlist_stock_notification_message": {
            "t-on-click": this.onClickWishlistStockNotificationMessage.bind(this),
        },
        "#wishlist_stock_notification_form_submit_button": {
            "t-on-click": this.onClickSubmitWishlistStockNotificationForm.bind(this),
        },
    };

    start() {
        this._applySearchParams();
        this._triggerVariantChange(this.el);
        this._startZoom();
        this._highlightReviewMessage();
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
        this._triggerVariantChange(ev.currentTarget.closest('.js_product'));
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
            ev.currentTarget.name === 'minus_button' ? -1 : 1
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

    _highlightReviewMessage() {
        if (router.current.highlight_message_id) {
            this.onClickReviewsLink();
        }
    }

    /**
     * Uncollapse the reviews.
     */
    onClickReviewsLink() {
        const reviewsContent = document.querySelector('#o_product_page_reviews_content');
        if (reviewsContent) {
            window.Collapse.getOrCreateInstance(reviewsContent).show();
        }
    }

    /**
     * Highlight the selected attributes (Color, Image, or Thumbnail).
     * @param {MouseEvent} ev - The event object.
     */
    onChangeAttribute( ev) {
        const target = ev.target;
        const parent = target.closest('.js_product');

        parent.querySelectorAll('label[name^="o_wsale_attribute_"]').forEach(el => {
            const input = el.querySelector('input');
            el.classList.toggle('active', input && input.checked);
        });

        const attrValueEl = target
            .closest('.variant_attribute, [name="variant_attribute"]')
            ?.querySelector('.attribute_value, [name="attribute_value"]');

        if (attrValueEl) {
            attrValueEl.innerText = target.dataset.valueName;
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

    onHoverPackagingButton(ev) {
        const parent = ev.target.closest(".js_product");
        const currentPackagingPrice = Number(this._getUoMPrice(parent).toFixed(2));
        const hoveredPackagingPrice = Number(
            parseFloat(
                ev.target.querySelector("input[name='uom_id']").dataset.packagingPrice
            ).toFixed(2)
        );
        if (currentPackagingPrice !== hoveredPackagingPrice) {
            parent
                .querySelector("p[name='packaging_price_value']")
                .querySelector(".oe_currency_value").textContent = this._priceToStr(
                hoveredPackagingPrice,
                false
            );
            parent.querySelector("span[name='packaging_price']").classList.remove("d-none");
        }
    }

    onMouseLeavePackagingButton(ev) {
        const parent = ev.target.closest(".js_product");
        parent.querySelector("span[name='packaging_price']").classList.add("d-none");
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
                this._changeAttribute('label[name^="o_wsale_attribute_], .o_variant_pills');
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
        if (images && !isEditorEnabled && newImages) {
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
        parent.querySelectorAll('button[name="add_to_cart"]').forEach(
            el => el.disabled = !isCombinationPossible
        );
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
        const addToCart = parent.querySelector('button[name="add_to_cart"]');
        const productTemplateId = parseInt(addToCart?.dataset?.productTemplateId);

        const combinationInfo = await this.waitFor(rpc('/website_sale/get_combination_info', {
            'product_template_id': productTemplateId,
            'product_id': parseInt(addToCart?.dataset?.productId),
            'combination': combination,
            'add_qty': parseFloat(parent.querySelector('input[name="add_qty"]')?.value),
            'uom_id': parseInt(parent.querySelector('input[name="uom_id"]:checked')?.value),
            'context': this.context,
            ...this._getOptionalCombinationInfoParams(parent),
        }));
        const attributeValueImages = await this.waitFor(rpc('/website_sale/get_attribute_images', {
            'product_template_id': productTemplateId,
            'combination': combination,
        }));
        if (combinationInfo.product_tags) {
            combinationInfo.product_tags = markup(combinationInfo.product_tags);
        }
        if (combinationInfo.out_of_stock_message) {
            combinationInfo.out_of_stock_message = markup(combinationInfo.out_of_stock_message);
        }
        combinationInfo.packaging_selector = markup(combinationInfo.packaging_selector);

        this._onChangeCombination(ev, parent, combinationInfo, attributeValueImages);
        this._checkExclusions(parent, combination);
    }

    _getUoMPrice(element) {
        return parseFloat(
            element.querySelector("input[name='uom_id']:checked")?.dataset.packagingPrice
        );
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
     * @param {Object} attributeValueImages
     */
    async _onChangeCombination(ev, parent, combination, attributeValueImages) {
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

        if ("packaging_prices" in combination) {
            this._handlePackagingInfo(parent, combination);
        }

        // handle GMC tracking
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
        const boxedPriceWrapper = parent.querySelector('#o_wsale_cta_wrapper_boxed_price');

        const preventSale = combination.prevent_sale;
        const hidePrice = combination.hide_price;
        productPrice?.classList.toggle('d-inline-block', !hidePrice);
        productPrice?.classList.toggle('d-none', hidePrice);
        boxedPriceWrapper?.classList.toggle('d-flex', !hidePrice);
        boxedPriceWrapper?.classList.toggle('d-none', hidePrice);
        quantity?.classList?.toggle('d-inline-flex', !preventSale);
        quantity?.classList?.toggle('d-none', preventSale);
        addToCart?.classList.toggle('d-inline-flex', !preventSale);
        addToCart?.classList.toggle('d-none', preventSale);
        contactUsButton?.classList?.toggle('d-none', !preventSale);
        contactUsButton?.classList?.toggle('d-flex', preventSale);

        if (contactUsButton) {
            const link = contactUsButton.querySelector('a');
            if (link && combination.display_name) {
                const linkUrl = new URL(link.href, window.location.origin);
                linkUrl.searchParams.set('subject', combination.display_name);
                link.href = linkUrl.toString();
            }
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

        Object.entries(attributeValueImages || {}).forEach(([valueId, imageUrl]) => {
            const input = parent.querySelector(`input[data-value-id="${valueId}"]`);
            const label = input?.closest('label[name="o_wsale_attribute_thumbnail_selector"]');
            if (label) {
                label.style.backgroundImage = `url(${imageUrl})`;
            }
        });

        this._toggleDisable(parent, isCombinationPossible && this.el.dataset.hasAvailableUoms);

        // Only update the images, tags and packaging selector if the product has changed.
        if (!combination.no_product_change) {
            this._updateProductImages(parent.closest('#product_detail_main'), combination.carousel);
            const productTags = parent.querySelector('.o_product_tags');
            productTags?.insertAdjacentHTML('beforebegin', htmlEscape(combination.product_tags));
            productTags?.remove();

            const packagingSelector = parent.querySelector('[name="packaging_selector"]');
            if (packagingSelector) {
                packagingSelector.insertAdjacentHTML(
                    'beforebegin', htmlEscape(combination.packaging_selector)
                );
                packagingSelector.remove();
            }
            // Toggle variant section visibility when UOM availability changes (edge case:
            // template has no attributes, only some variants have UOMs).
            const variantSection = parent.querySelector(
                '.o_wsale_product_details_content_section_attributes'
            );
            if (variantSection) {
                const hasAttributes = parent.querySelector(
                    '.o_wsale_product_page_variants li.variant_attribute'
                );
                const hasPackaging = parent.querySelector(
                    '[name="packaging_selector"] .o_wsale_product_page_variants'
                );
                variantSection.classList.toggle('d-none', !hasAttributes && !hasPackaging);
            }
        }

        const productIdElements = parent.querySelectorAll('[data-product-id]');
        productIdElements.forEach(el => el.dataset.productId = combination.product_id || 0);
        parent.dispatchEvent(new CustomEvent(
            'product_changed', { detail: { productId: combination.product_id || 0 } }
        ));

        this.handleCustomValues(ev.target);

        const has_max_combo_quantity = 'max_combo_quantity' in combination
        if (!combination.is_storable && !has_max_combo_quantity) return;
        if (!combination.product_id) return; // If the product is dynamic.

        const addQtyInput = parent.querySelector('input[name="add_qty"]');
        const qty = parseFloat(addQtyInput?.value) || 1;
        const ctaWrapper = parent.querySelector('#o_wsale_cta_wrapper');
        ctaWrapper.classList.replace('d-none', 'd-flex');
        ctaWrapper.classList.remove('out_of_stock');

        if (!combination.allow_out_of_stock_order) {
            const unavailableQty = await this.waitFor(this._getUnavailableQty(combination));
            combination.free_qty -= unavailableQty;
            if (combination.free_qty < 0) {
                combination.free_qty = 0;
            }
            if (addQtyInput) {
                addQtyInput.dataset.max = combination.free_qty || 1;
                if (qty > combination.free_qty) {
                    addQtyInput.value = addQtyInput.dataset.max;
                }
            }
            if (combination.free_qty < 1 && !combination.prevent_sale) {
                ctaWrapper.classList.replace('d-flex', 'd-none');
                ctaWrapper.classList.add('out_of_stock');
            }
        } else if (has_max_combo_quantity) {
            if (addQtyInput) {
                addQtyInput.dataset.max = combination.max_combo_quantity || 1;
                if (qty > combination.max_combo_quantity) {
                    addQtyInput.value = addQtyInput.dataset.max;
                }
            }
            if (combination.max_combo_quantity < 1 && !combination.prevent_sale) {
                ctaWrapper.classList.replace('d-flex', 'd-none');
                ctaWrapper.classList.add('out_of_stock');
            }
        }

        // needed xml-side for formatting of remaining qty
        combination.formatQuantity = qty => {
            if (Number.isInteger(qty)) {
                return qty;
            } else {
                const decimals = Math.max(0, Math.ceil(-Math.log10(combination.uom_rounding)));
                return formatFloat(qty, { digits: [false, decimals] });
            }
        }

        document.querySelector('.oe_website_sale')
            .querySelectorAll('.availability_message_' + combination.product_template)
            .forEach(el => el.remove());
        if (combination.out_of_stock_message) {
            const outOfStockMessage = document.createElement('div');
            setElementContent(outOfStockMessage, combination.out_of_stock_message);
            combination.has_out_of_stock_message = !!outOfStockMessage.textContent.trim();
        }
        this.el.querySelector('div.availability_messages').append(renderToFragment(
            'website_sale.product_availability', combination
        ));
        if (this.el.querySelector('.o_add_wishlist_dyn')) {
            const messageEl = this.el.querySelector('div.availability_messages');
            if (messageEl && !this.el.querySelector('#stock_wishlist_message')) {
                this.services['public.interactions'].stopInteractions(messageEl);
                messageEl.append(
                    renderToElement('website_sale.product_availability_wishlist', combination)
                    || ''
                );
                this.services['public.interactions'].startInteractions(messageEl);
            }
        }
    }

    async _getUnavailableQty(combination) {
        return parseInt(combination.cart_qty);
    }

    /**
     * Update the packaging prices.
     * @private
     * @param {Element} parent
     * @param {Object} combination
     * */
    _handlePackagingInfo(parent, combination) {
        Object.entries(combination.packaging_prices).forEach(([uomId, price]) => {
            const el = parent.querySelector(`input[name="uom_id"]#uom-${uomId}`);
            if (!el) {
                return;
            }

            el.dataset.packagingPrice = price;
        });
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

    onClickProductStockNotificationMessage(ev) {
        const partnerEmail = document.querySelector('#wsale_user_email').value;
        const emailInputEl = document.querySelector('#stock_notification_input');

        emailInputEl.value = partnerEmail;
        this._handleClickStockNotificationMessage(ev);
    }

    onClickSubmitProductStockNotificationForm(ev) {
        const productId = parseInt(ev.currentTarget.dataset.productId);
        this._handleClickSubmitStockNotificationForm(ev, productId);
    }

    _handleClickStockNotificationMessage(ev) {
        ev.currentTarget.classList.add('d-none');
        ev.currentTarget.parentElement.querySelector('#stock_notification_form').classList.remove('d-none');
    }

    async _handleClickSubmitStockNotificationForm(ev, productId) {
        const stockNotificationEl = ev.currentTarget.closest('#stock_notification_div');
        const formEl = stockNotificationEl.querySelector('#stock_notification_form');
        const email = stockNotificationEl.querySelector('#stock_notification_input').value.trim();

        if (!isEmail(email)) {
            return this._displayEmailIncorrectMessage(stockNotificationEl);
        }

        try {
            await this.waitFor(rpc(
                '/shop/add/stock_notification', { product_id: productId, email }
            ));
        } catch {
            this._displayEmailIncorrectMessage(stockNotificationEl);
            return;
        }
        const message = stockNotificationEl.querySelector('#stock_notification_success_message');
        message.classList.remove('d-none');
        formEl.classList.add('d-none');
    }

    _displayEmailIncorrectMessage(stockNotificationEl) {
        const incorrectIconEl = stockNotificationEl.querySelector('#stock_notification_input_incorrect');
        incorrectIconEl.classList.remove('d-none');
    }

    onClickWishlistStockNotificationMessage(ev) {
        this._handleClickStockNotificationMessage(ev);
    }

    onClickSubmitWishlistStockNotificationForm(ev) {
        const productId = ev.currentTarget.closest('article').dataset.productId;
        this._handleClickSubmitStockNotificationForm(ev, productId);
    }
}

registry.category('public.interactions').add('website_sale.product_page', ProductPage);
