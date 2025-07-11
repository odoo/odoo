import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { hasTouch, isBrowserFirefox } from '@web/core/browser/feature_detection';
import { utils as uiUtils } from '@web/core/ui/ui_service';
import '@website/libs/zoomodoo/zoomodoo';
import { ProductImageViewer } from '@website_sale/js/components/website_sale_image_viewer';
import VariantMixin from '@website_sale/js/sale_variant_mixin';

export class WebsiteSale extends Interaction {
    static selector = '.oe_website_sale';
    dynamicContent = {
        'form .js_product:first input[name="add_qty"]': { 't-on-change': this.onChangeAddQuantity },
        'a.js_add_cart_json': { 't-on-click.prevent': this.onChangeQuantity },
        '.a-submit': { 't-on-click': this.onClickSubmit },
        'form.js_attributes input, form.js_attributes select': {
            't-on-change.prevent': this.onChangeAttribute,
        },
        '.o_wsale_products_searchbar_form': { 't-on-submit': this.onSubmitSaleSearch },
        '#add_to_cart, .o_we_buy_now, #products_grid .o_wsale_product_btn .a-submit': {
            't-on-click.prevent': this.onClickAdd,
        },
        '.js_main_product [data-attribute_exclusions]': { 't-on-change': this.onChangeVariant },
        '.o_product_page_reviews_link': { 't-on-click': this.onClickReviewsLink },
        '.o_wsale_filmstrip_wrapper': {
            't-on-mousedown': this.onMouseDown,
            't-on-mouseleave': this.onMouseLeave,
            't-on-mouseup': this.onMouseUp,
            't-on-mousemove.prevent': this.onMouseMove,
            't-on-click': this.onClickHandler,
        },
        'form[name="o_wsale_confirm_order"]': { 't-on-submit': this.locked(this.onClickConfirmOrder) },
        '.o_wsale_attribute_search_bar': { 't-on-input': this.searchAttributeValues },
        '.o_wsale_variant_pills_shop': { 't-on-click': this.onClickPillsAttribute },
        '.o_wsale_view_more_btn': { 't-on-click': this.onToggleViewMoreLabel },
        '.css_attribute_color input': { 't-on-change': this.onChangeColorAttribute },
        '.o_variant_pills': { 't-on-click': this.onChangePillsAttribute },
    }

    setup() {
        this.isWebsite = true;
        this.filmStripStartX = 0;
        this.filmStripIsDown = false;
        this.filmStripScrollLeft = 0;
        this.filmStripMoved = false;
    }

    start() {
        this._applyHash();

        // This has to be triggered to compute the "out of stock" feature and the hash variant changes
        this.triggerVariantChange(this.el);

        this._startZoom();

        // Triggered when selecting a variant of a product in a carousel element
        window.addEventListener("hashchange", (ev) => {
            this._applyHash();
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
        if (!this.filmStripIsDown) {
            return;
        }
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

    _applyHash() {
        const params = new URLSearchParams(window.location.hash.substring(1));
        if (params.get("attribute_values")) {
            const attributeValueIds = params.get("attribute_values").split(',');
            const inputs = document.querySelectorAll(
                'input.js_variant_change, select.js_variant_change option'
            );
            inputs.forEach((element) => {
                if (attributeValueIds.includes(element.dataset.attributeValueId)) {
                    if (element.tagName === "INPUT") {
                        element.checked = true;
                    } else if (element.tagName === "OPTION") {
                        element.selected = true;
                    }
                }
            });
            this._changeAttribute(['.css_attribute_color', '.o_variant_pills']);
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
            // Avoid adding new entries in session history by replacing the current one
            history.replaceState(null, '', '#attribute_values=' + attributeIds.join(','));
        }
    }

    /**
     * Set the checked values active.
     *
     * @param {Array} valueSelectors Selectors
     */
    _changeAttribute(valueSelectors) {
        Array.from(this.el.querySelectorAll(valueSelectors)).forEach((el) => {
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
        // Zoom on hover (except on mobile)
        if (salePage.dataset.ecomZoomAuto && !uiUtils.isSmall()) {
            const images = salePage.querySelectorAll("img[data-zoom]");
            for (const image of images) {
                const $image = $(image);
                const callback = () => {
                    $image.zoomOdoo({
                        event: "mouseenter",
                        attach: this._getProductImageContainerSelector(),
                        preventClicks: salePage.dataset.ecomZoomClick,
                        attachToTarget: this._getProductImageLayout() === "grid",
                    });
                    image.dataset.zoom = 1;
                };
                image.addEventListener('load', callback);
                this.zoomCleanup.push(() => {
                    image.removeEventListener('load', callback);
                    const zoomOdoo = $image.data("zoomOdoo");
                    if (zoomOdoo) {
                        zoomOdoo.hide();
                        $image.unbind();
                    }
                });
                if (image.complete) {
                    callback();
                }
            }
        }
        // Zoom on click
        if (salePage.dataset.ecomZoomClick) {
            // In this case we want all the images not just the ones that are "zoomables"
            const images = salePage.querySelectorAll(".product_detail_img");
            for (const image of images ) {
                const handler = () => {
                    if (salePage.dataset.ecomZoomAuto) {
                        // Remove any flyout
                        const flyouts = document.querySelectorAll(".zoomodoo-flyout");
                        for (const flyout of flyouts) {
                            flyout.remove();
                        }
                    }
                    this.call("dialog", "add", ProductImageViewer, {
                        selectedImageIdx: [...images].indexOf(image),
                        images,
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
        // TODO(loti): check if single or multiple images.
        let images = productContainer.querySelectorAll(this._getProductImageContainerSelector());
        // When using the web editor, don't reload this or the images won't
        // be able to be edited depending on if this is done loading before
        // or after the editor is ready.
        if (images.length && !this._isEditorEnabled()) {
            images.forEach(image => image.after(newImages));
            images.forEach(image => image.remove());
            images = newImages;
            // Update the sharable image (only work for Pinterest).
            const shareImageSrc = images[0].querySelector('img').src;
            document.querySelector('meta[property="og:image"]')
                .setAttribute('content', shareImageSrc);

            // TODO(loti): probably nok if multiple images.
            if (images.id === 'o-carousel-product') {
                // TODO(loti): check this.
                const carousel = new Carousel(images);
                carousel.to(0);
            }
            this._startZoom();
            // fix issue with carousel height
            // TODO(loti): check if needed.
            this.services['public.interactions'].stopInteractions(images);
            this.services['public.interactions'].startInteractions(images);
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    async onClickAdd(ev) {
        var def = () => {
            this._updateRootProduct((ev.currentTarget).closest('form'));
            const isBuyNow = ev.currentTarget.classList.contains('o_we_buy_now');
            const isConfigured = ev.currentTarget.parentElement.id === 'add_to_cart_wrap';
            const showQuantity = Boolean(ev.currentTarget.dataset.showQuantity);
            return this.call('cart', 'add', this.rootProduct, {
                isBuyNow: isBuyNow,
                isConfigured: isConfigured,
                showQuantity: showQuantity,
            });
        };
        if ($('.js_add_cart_variants').children().length) {
            await this._getCombinationInfo(ev);
            return !(ev.target).closest('.js_product').classList.contains('.css_not_available')
                ? def() : Promise.resolve();
        }
        return def();
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
        const previousQty = parseFloat(input.value || 0, 10);
        const quantity = (
            ev.currentTarget.querySelector('i').classList.contains('oi-minus') ? -1 : 1
        ) + previousQty;
        const newQty = quantity > min ? (quantity < max ? quantity : max) : min;

        if (newQty !== previousQty) {
            input.value = newQty;
            input.dispatchEvent(
                new Event('change', {bubbles: true})
            );  // Trigger `onChangeVariant` through .js_main_product
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

        document.querySelectorAll(`#${input.dataset.containerId} .form-check`).forEach(item =>{
            const labelText = item.querySelector('.form-check-label').textContent.toLowerCase();
            item.style.display = labelText.includes(searchValue) ? '' : 'none'
        });
    }

    /**
     * Highlight selected pill
     *
     * @param {MouseEvent} ev
     */
    onClickPillsAttribute(ev) {
        if (ev.target.tagName === "LABEL" || ev.target.tagName === "INPUT") {
            return;
        }
        const checkbox = ev.target.closest('.o_wsale_variant_pills_shop').querySelector("input");
        checkbox.click();
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
        const parent = ev.currentTarget.closest('form');
        if (parent) this.triggerVariantChange(parent);
    }

    /**
     * @param {Event} ev
     */
    onClickSubmit(ev) {
        if ($(ev.currentTarget).is('#add_to_cart, #products_grid .a-submit')) {
            return;
        }
        var $aSubmit = $(ev.currentTarget);
        if (!ev.defaultPrevented && !$aSubmit.is(".disabled")) {
            ev.preventDefault();
            $aSubmit.closest('form')[0].requestSubmit();
        }
        if ($aSubmit.hasClass('a-submit-disable')) {
            $aSubmit.addClass("disabled");
        }
        if ($aSubmit.hasClass('a-submit-loading')) {
            var loading = '<span class="fa fa-cog fa-spin"/>';
            var fa_span = $aSubmit.find('i[class*="fa"]');
            if (fa_span.length) {
                fa_span.replaceWith(loading);
            } else {
                $aSubmit.append(loading);
            }
        }
    }

    /**
     * @param {Event} ev
     */
    onChangeAttribute(ev) {
        const productGrid = this.el.querySelector(".o_wsale_products_grid_table_wrapper");
        if (productGrid) {
            productGrid.classList.add("opacity-50");
        }
        const form = ev.currentTarget.closest('form');
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
                    tags.add(filter.value)
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
        window.location.href = `${url.pathname}?${searchParams.toString()}`;
    }

    /**
     * @param {Event} ev
     */
    onSubmitSaleSearch(ev) {
        if (!this.$('.dropdown_sorty_by').length) {
            return;
        }
        var $this = $(ev.currentTarget);
        if (!ev.defaultPrevented && !$this.is(".disabled")) {
            ev.preventDefault();
            var oldurl = $this.attr('action');
            oldurl += (oldurl.indexOf("?")===-1) ? "?" : "";
            if ($this.find('[name=noFuzzy]').val() === "true") {
                oldurl += '&noFuzzy=true';
            }
            var search = $this.find('input.search-query');
            window.location = oldurl + '&' + search.attr('name') + '=' + encodeURIComponent(search.val());
        }
    }

    /**
     * Toggles the add to cart button depending on the possibility of the
     * current combination.
     */
    _toggleDisable($parent, isCombinationPossible) {
        VariantMixin._toggleDisable.apply(this, arguments);
        $parent.find("#add_to_cart").toggleClass('disabled', !isCombinationPossible);
        $parent.find(".o_we_buy_now").toggleClass('disabled', !isCombinationPossible);
    }

    /**
     * Write the properties of the form elements in the DOM to prevent the
     * current selection from being lost when activating the web editor.
     */
    onChangeVariant(ev) {
        var $component = $(ev.currentTarget).closest('.js_product');
        $component.find('input').each(function () {
            var $el = $(this);
            $el.attr('checked', $el.is(':checked'));
        });
        $component.find('select option').each(function () {
            var $el = $(this);
            $el.attr('selected', $el.is(':selected'));
        });

        this._setUrlHash();

        return VariantMixin.onChangeVariant.apply(this, arguments);
    }

    onClickReviewsLink() {
        $('#o_product_page_reviews_content').collapse('show');
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
        let $eventTarget = $(ev.target);
        var $parent = $eventTarget.closest('.js_product');
        $parent.find('.css_attribute_color')
            .removeClass("active")
            .filter(':has(input:checked)')
            .addClass("active");
        let $attrValueEl = $eventTarget.closest('.variant_attribute').find('.attribute_value')[0];
        if ($attrValueEl) {
            $attrValueEl.innerText = $eventTarget.data('value_name');
        }
    }

    onChangePillsAttribute(ev) {
        const radio = ev.target.closest('.o_variant_pills').querySelector("input");
        radio.click();  // Trigger onChangeVariant.
        var $parent = $(ev.target).closest('.js_product');
        $parent.find('.o_variant_pills')
            .removeClass("active border-primary text-primary-emphasis bg-primary-subtle")
            .filter(':has(input:checked)')
            .addClass("active border-primary text-primary-emphasis bg-primary-subtle");
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
        const quantity = parseFloat(form.querySelector('input[name="add_qty"]')?.value);
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
                    el.dataset.custom_product_template_attribute_value_id
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

registry
    .category('public.interactions')
    .add('website_sale.website_sale', WebsiteSale);
