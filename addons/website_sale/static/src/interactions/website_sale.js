import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { hasTouch, isBrowserFirefox } from '@web/core/browser/feature_detection';
import { redirect, url } from '@web/core/utils/urls';
import { uniqueId } from '@web/core/utils/functions';
import { markup } from '@odoo/owl';
import wSaleUtils from '@website_sale/js/website_sale_utils';
import { ProductImageViewer } from '@website_sale/js/components/website_sale_image_viewer';
import VariantMixin from '@website_sale/js/variant_mixin';

export class WebsiteSale extends Interaction {
    static selector = '.oe_website_sale';
    dynamicContent = {
        '.js_main_product input[name="add_qty"]': { 't-on-change': this.onChangeAddQuantity },
        'a.js_add_cart_json': { 't-on-click.prevent': this.onChangeQuantity },
        'form.js_attributes input, form.js_attributes select': {
            't-on-change.prevent': this.onChangeAttribute,
        },
        '.o_wsale_products_searchbar_form': { 't-on-submit': this.onSubmitSaleSearch },
        '#add_to_cart, .o_we_buy_now, #products_grid .o_wsale_product_btn .a-submit': {
            't-on-click.prevent': this.onClickAdd,
        },
        '.js_main_product [data-attribute-exclusions]': { 't-on-change': this.onChangeVariant },
        '.o_product_page_reviews_link': { 't-on-click': this.onClickReviewsLink },
        '.o_wsale_filmstrip_wrapper': {
            't-on-mousedown': this.onMouseDown,
            't-on-mouseleave': this.onMouseLeave,
            't-on-mouseup': this.onMouseUp,
            't-on-mousemove': this.onMouseMove,
            't-on-click': this.onClickHandler,
        },
        'form[name="o_wsale_confirm_order"]': {
            't-on-submit': this.locked(this.onClickConfirmOrder),
        },
        '.o_wsale_attribute_search_bar': { 't-on-input': this.searchAttributeValues },
        '.o_wsale_view_more_btn': { 't-on-click': this.onToggleViewMoreLabel },
        '.css_attribute_color input': { 't-on-change': this.onChangeColorAttribute },
        'label[name="o_wsale_attribute_image_selector"] input': {
            't-on-change': this.onChangeImageAttribute,
        },
        '.o_variant_pills': { 't-on-click': this.onChangePillsAttribute },
    };

    setup() {
        this.isWebsite = true;
        this.filmStripStartX = 0;
        this.filmStripIsDown = false;
        this.filmStripScrollLeft = 0;
        this.filmStripMoved = false;
        this.imageRatio = this.el.dataset.imageRatio;
    }

    start() {
        this._applySearch();

        // This has to be triggered to compute the "out of stock" feature and the hash variant changes
        this.triggerVariantChange(this.el);

        this._startZoom();

        // Triggered when selecting a variant of a product in a carousel element
        window.addEventListener('hashchange', (ev) => {
            this._applySearch();
            this.triggerVariantChange(this.el);
        });

        // This allows conditional styling for the filmstrip
        const filmstripContainer = this.el.querySelector('#o_wsale_categories_filmstrip');
        const filmstripWrapper = this.el.querySelector('.o_wsale_filmstrip_wrapper');
        const isFilmstripScrollable = filmstripWrapper
            ? filmstripWrapper.scrollWidth > filmstripWrapper.clientWidth
            : false;

        if (isBrowserFirefox() || hasTouch() || !isFilmstripScrollable) {
            filmstripContainer?.classList.add('o_wsale_filmstrip_fancy_disabled');
        }
    }

    destroy() {
        this._cleanupZoom();
    }

    onMouseDown(ev) {
        this.filmStripIsDown = true;
        this.filmStripStartX = ev.pageX - ev.currentTarget.offsetLeft;
        this.filmStripScrollLeft = ev.currentTarget.scrollLeft;
        this.filmStripMoved = false;
    }

    onMouseLeave(ev) {
        if (!this.filmStripIsDown) {
            return;
        }
        ev.currentTarget.classList.remove('activeDrag');
        this.filmStripIsDown = false
    }

    onMouseUp(ev) {
        this.filmStripIsDown = false;
        ev.currentTarget.classList.remove('activeDrag');
    }

    onMouseMove(ev) {
        if (!this.filmStripIsDown) return;
        ev.preventDefault();
        ev.currentTarget.classList.add('activeDrag');
        this.filmStripMoved = true;
        const x = ev.pageX - ev.currentTarget.offsetLeft;
        const walk = (x - this.filmStripStartX) * 2;
        ev.currentTarget.scrollLeft = this.filmStripScrollLeft - walk;
    }

    onClickHandler(ev) {
        if (this.filmStripMoved) {
            ev.stopPropagation();
            ev.preventDefault();
        }
    }

    _applySearch() {
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
            inputs.forEach((element) => {
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
     * Sets the url hash from the selected product options.
     */
    _setUrlHash() {
        const inputs = document.querySelectorAll(
            'input.js_variant_change:checked, select.js_variant_change option:checked'
        );
        let attributeIds = [];
        inputs.forEach((element) => attributeIds.push(element.dataset.attributeValueId));
        if (attributeIds.length > 0) {
            const params = new URLSearchParams(window.location.search);
            params.set('attribute_values', attributeIds.join(','))
            // Avoid adding new entries in session history by replacing the current one
            history.replaceState(null, '', url(window.location.pathname, Object.fromEntries(params)));
        }
    }

    /**
     * Set the checked values active.
     *
     * @param {String} selector - The selector matching the attributes to change.
     */
    _changeAttribute(selector) {
        this.el.querySelectorAll(selector).forEach((el) => {
            const input = el.querySelector('input');
            const isActive = input?.checked;
            el.classList.toggle('active', isActive);
            if (isActive) input.dispatchEvent(new Event('change', { bubbles: true }));
        });
    }

    _getProductImageLayout() {
        return document.querySelector("#product_detail_main").dataset.image_layout;
    }

    _getProductImageWidth() {
        return document.querySelector("#product_detail_main").dataset.image_width;
    }

    _getProductImageContainerSelector() {
        return {
            'carousel': "#o-carousel-product",
            'grid': "#o-grid-product",
        }[this._getProductImageLayout()];
    }

    _isEditorEnabled() {
        return document.body.classList.contains("editor_enable");
    }

    _startZoom() {
        const salePage = document.querySelector(".o_wsale_product_page");
        if (!salePage || this._getProductImageWidth() === "none") {
            return;
        }
        this._cleanupZoom();
        this.zoomCleanup = [];
        // Zoom on click
        if (salePage.dataset.ecomZoomClick) {
            // In this case we want all the images not just the ones that are "zoomables"
            const images = this.el.querySelectorAll('.product_detail_img');
            for (const [idx, image] of images.entries()) {
                const handler = () => {
                    this.services.dialog.add(ProductImageViewer, {
                        selectedImageIdx: idx,
                        images,
                        imageRatio: this.imageRatio,
                    });
                };
                image.addEventListener("click", handler);
                this.zoomCleanup.push(() => {
                    image.removeEventListener("click", handler);
                });
            }
        }
    }

    _cleanupZoom() {
        if (!this.zoomCleanup || !this.zoomCleanup.length) {
            return;
        }
        for (const cleanup of this.zoomCleanup) {
            cleanup();
        }
        this.zoomCleanup = undefined;
    }

    /**
     * On website, we display a carousel instead of only one image
     */
    _updateProductImage(productContainer, newImages) {
        let images = productContainer.querySelector(this._getProductImageContainerSelector());
        // When using the web editor, don't reload this or the images won't
        // be able to be edited depending on if this is done loading before
        // or after the editor is ready.
        if (images && !this._isEditorEnabled() && newImages ) {
            images.insertAdjacentHTML('beforebegin', markup(newImages));
            images.remove();

            // Re-query the latest images.
            images = productContainer.querySelector(this._getProductImageContainerSelector());
            // Update the sharable image (only work for Pinterest).
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
     * @param {MouseEvent} ev
     */
    async onClickAdd(ev) {
        const el = ev.currentTarget;
        if (this.el.querySelector('.js_add_cart_variants')?.children?.length) {
            await this.waitFor(this._getCombinationInfo(ev));
            if (!ev.target.closest('.js_product').classList.contains('.css_not_available')) {
                return this._addToCart(el);
            }
        } else {
            return this._addToCart(el);
        }
    }

    /**
     * @param {HTMLElement} el
     */
    async _addToCart(el) {
        const form = wSaleUtils.getClosestProductForm(el);
        this._updateRootProduct(form);
        const isBuyNow = el.classList.contains('o_we_buy_now');
        const isConfigured = el.parentElement.id === 'add_to_cart_wrap';
        const showQuantity = Boolean(el.dataset.showQuantity);
        return this.services['cart'].add(this.rootProduct, {
            isBuyNow: isBuyNow,
            isConfigured: isConfigured,
            showQuantity: showQuantity,
        });
    }

    /**
     * Event handler to increase or decrease quantity from the product page.
     *
     * @param {MouseEvent} ev
     */
    onChangeQuantity(ev) {
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
     * Search attribute values based on the input text.
     *
     * @param {Event} ev
     */
    searchAttributeValues(ev) {
        const input = ev.target;
        const searchValue = input.value.toLowerCase();

        document.querySelectorAll(`#${input.dataset.containerId} .form-check`).forEach(item => {
            const labelText = item.querySelector('.form-check-label').textContent.toLowerCase();
            item.style.display = labelText.includes(searchValue) ? '' : 'none'
        });
    }

    /**
     * Toggle the button text between "View More" and "View Less"
     *
     * @param {MouseEvent} ev
     */
    onToggleViewMoreLabel(ev) {
        const button = ev.target;
        const isExpanded = button.getAttribute('aria-expanded') === 'true';

        button.innerHTML = isExpanded ? "View Less" : "View More";
    }

    /**
     * When the quantity is changed, we need to query the new price of the product.
     * Based on the pricelist, the price might change when quantity exceeds a certain amount.
     *
     * @param {MouseEvent} ev
     */
    onChangeAddQuantity(ev) {
        const parent = wSaleUtils.getClosestProductForm(ev.currentTarget);
        if (parent) this.triggerVariantChange(parent);
    }

    /**
     * @param {Event} ev
     */
    onChangeAttribute(ev) {
        const productGrid = this.el.querySelector('.o_wsale_products_grid_table_wrapper');
        if (productGrid) {
            productGrid.classList.add('opacity-50');
        }
        const form = wSaleUtils.getClosestProductForm(ev.currentTarget);
        const filters = form.querySelectorAll('input:checked, select');
        const attributeValues = new Map();
        const tags = new Set();
        for (const filter of filters) {
            if (filter.value) {
                if (filter.name === 'attribute_value') {
                    // Group attribute value ids by attribute id.
                    const [attributeId, attributeValueId] = filter.value.split('-');
                    const valueIds = attributeValues.get(attributeId) ?? new Set();
                    valueIds.add(attributeValueId);
                    attributeValues.set(attributeId, valueIds);
                } else if (filter.name === 'tags') {
                    tags.add(filter.value);
                }
            }
        }
        const url = new URL(form.action);
        const searchParams = url.searchParams;
        // Aggregate all attribute values belonging to the same attribute into a single
        // `attribute_values` search param.
        for (const entry of attributeValues.entries()) {
            searchParams.append('attribute_values', `${entry[0]}-${[...entry[1]].join(',')}`);
        }
        // Aggregate all tags into a single `tags` search param.
        if (tags.size) {
            searchParams.set('tags', [...tags].join(','));
        }
        redirect(`${url.pathname}?${searchParams.toString()}`);
    }

    /**
     * @param {Event} ev
     */
    onSubmitSaleSearch(ev) {
        if (!this.el.querySelector('.dropdown_sorty_by')) return;
        const form = ev.currentTarget;
        if (!ev.defaultPrevented && !form.matches('.disabled')) {
            ev.preventDefault();
            const url = new URL(form.action);
            const searchParams = url.searchParams;
            if (form.querySelector('[name=noFuzzy]')?.value === 'true') {
                searchParams.set('noFuzzy', 'true');
            }
            const input = form.querySelector('input.search-query');
            searchParams.set(input.name, input.value);
            redirect(`${url.pathname}?${searchParams.toString()}`);
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

        this._setUrlHash();

        if (!parent.dataset.uniqueId) {
            parent.dataset.uniqueId = uniqueId();
        }
        this._throttledGetCombinationInfo(this, parent.dataset.uniqueId)(ev);
    }

    onClickReviewsLink() {
        Collapse.getOrCreateInstance(
            document.querySelector('#o_product_page_reviews_content')
        ).show();
    }

    /**
     * Prevent multiple clicks on the confirm button when the form is submitted.
     */
    onClickConfirmOrder(ev) {
        const button = ev.currentTarget.querySelector('button[type="submit"]');
        button.disabled = true;
        // TODO(loti): "random" timeout seems brittle.
        this.waitForTimeout(() => button.disabled = false, 5000);
    }

    /**
     * Highlight selected color
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
     * Highlight selected image
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

    onChangePillsAttribute(ev) {
        const radio = ev.target.closest('.o_variant_pills').querySelector('input');
        radio.click();  // Trigger onChangeVariant.
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

    // -------------------------------------
    // Utils
    // -------------------------------------

    /**
     * Update the root product during based on the form elements.
     *
     * @param {HTMLFormElement} form - The form in which the product is.
     */
    _updateRootProduct(form) {
        const productId = parseInt(
            form.querySelector('input[type="hidden"][name="product_id"]')?.value
        );
        const productEl = form.closest('.js_product') ?? form;
        const quantity = parseFloat(productEl.querySelector('input[name="add_qty"]')?.value);
        const uomId = this._getUoMId(form);
        const isCombo = form.querySelector(
            'input[type="hidden"][name="product_type"]'
        )?.value === 'combo';
        this.rootProduct = {
            ...(productId ? {productId: productId} : {}),
            productTemplateId: parseInt(form.querySelector(
                'input[type="hidden"][name="product_template_id"]',
            ).value),
            ...(quantity ? {quantity: quantity} : {}),
            ...(uomId ? {uomId: uomId} : {}),
            ptavs: this._getSelectedPTAV(form),
            productCustomAttributeValues: this._getCustomPTAVValues(form),
            noVariantAttributeValues: this._getSelectedNoVariantPTAV(form),
            ...(isCombo ? {isCombo: isCombo} : {}),
        };
    }

    /**
     * Return the selected stored PTAV(s) of in the provided form.
     *
     * @param {HTMLFormElement} form - The form in which the product is.
     *
     * @returns {Number[]} - The selected stored attribute(s), as a list of
     *      `product.template.attribute.value` ids.
     */
    _getSelectedPTAV(form) {
        const selectedPTAVElements = form.querySelectorAll([
            '.js_product input.js_variant_change:not(.no_variant):checked',
            '.js_product select.js_variant_change:not(.no_variant)'
        ].join(','));
        let selectedPTAV = [];
        for(const el of selectedPTAVElements) {
            selectedPTAV.push(parseInt(el.value));
        }
        return selectedPTAV;
    }

    /**
     * Return the custom PTAV(s) values in the provided form.
     *
     * @param {HTMLFormElement} form - The form in which the product is.
     *
     * @returns {{id: number, value: string}[]} An array of objects where each object contains:
     *      - `custom_product_template_attribute_value_id`: The ID of the custom attribute.
     *      - `custom_value`: The value assigned to the custom attribute.
     */
    _getCustomPTAVValues(form) {
        const customPTAVsValuesElements = form.querySelectorAll('.variant_custom_value');
        let customPTAVsValues = [];
        for(const el of customPTAVsValuesElements) {
            customPTAVsValues.push({
                'custom_product_template_attribute_value_id': parseInt(
                    el.dataset.customProductTemplateAttributeValueId
                ),
                'custom_value': el.value,
            });
        }
        return customPTAVsValues;
    }

    /**
     * Return the selected non-stored PTAV(s) of the product in the provided form.
     *
     * @param {HTMLFormElement} form - The form in which the product is.
     *
     * @returns {Number[]} - The selected non-stored attribute(s), as a list of
     *      `product.template.attribute.value` ids.
     */
    _getSelectedNoVariantPTAV(form) {
        const selectedNoVariantPTAVElements = form.querySelectorAll([
            'input.no_variant.js_variant_change:checked',
            'select.no_variant.js_variant_change',
        ].join(','));
        let selectedNoVariantPTAV = [];
        for(const el of selectedNoVariantPTAVElements) {
            selectedNoVariantPTAV.push(parseInt(el.value));
        }
        return selectedNoVariantPTAV;
    }
}

// TODO(loti): temporary hack. VariantMixin will be dropped.
Object.assign(WebsiteSale.prototype, VariantMixin);

registry.category('public.interactions').add('website_sale.website_sale', WebsiteSale);
