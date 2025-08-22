import { hasTouch, isBrowserFirefox } from "@web/core/browser/feature_detection";
import { utils as uiUtils } from "@web/core/ui/ui_service";
import publicWidget from "@web/legacy/js/public/public_widget";
import "@website/libs/zoomodoo/zoomodoo";
import { ProductImageViewer } from "@website_sale/js/components/website_sale_image_viewer";
import VariantMixin from "@website_sale/js/sale_variant_mixin";

export const WebsiteSale = publicWidget.Widget.extend(VariantMixin, {
    selector: '.oe_website_sale',
    events: {
        'change form .js_product:first input[name="add_qty"]': '_onChangeAddQuantity',
        'click a.js_add_cart_json': '_onChangeQuantity',
        'change form.js_attributes input, form.js_attributes select': '_onChangeAttribute',
        'submit .o_wsale_products_searchbar_form': '_onSubmitSaleSearch',
        'click #add_to_cart, .o_we_buy_now, #products_grid .o_wsale_product_btn .a-submit': '_onClickAdd',
        'change .js_main_product [data-attribute_exclusions]': 'onChangeVariant',
        'click .o_product_page_reviews_link': '_onClickReviewsLink',
        'mousedown .o_wsale_filmstrip_wrapper': '_onMouseDown',
        'mouseleave .o_wsale_filmstrip_wrapper': '_onMouseLeave',
        'mouseup .o_wsale_filmstrip_wrapper': '_onMouseUp',
        'mousemove .o_wsale_filmstrip_wrapper': '_onMouseMove',
        'click .o_wsale_filmstrip_wrapper' : '_onClickHandler',
        'submit': '_onClickConfirmOrder',
        'input .o_wsale_attribute_search_bar': '_searchAttributeValues',
        'click .o_wsale_view_more_btn': '_onToggleViewMoreLabel',
        'change .css_attribute_color input': '_onChangeColorAttribute',
        'click .o_variant_pills': '_onChangePillsAttribute',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this.isWebsite = true;
        this.filmStripStartX = 0;
        this.filmStripIsDown = false;
        this.filmStripScrollLeft = 0;
        this.filmStripMoved = false;
    },
    /**
     * @override
     */
    start() {
        const def = this._super(...arguments);

        this._applyHash();

        // This has to be triggered to compute the "out of stock" feature and the hash variant changes
        this.triggerVariantChange(this.$el);

        this._startZoom();

        // Triggered when selecting a variant of a product in a carousel element
        window.addEventListener("hashchange", (ev) => {
            this._applyHash();
            this.triggerVariantChange(this.$el);
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

        return def;
    },
    destroy() {
        this._super.apply(this, arguments);
        this._cleanupZoom();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _onMouseDown: function (ev) {
        this.filmStripIsDown = true;
        this.filmStripStartX = ev.pageX - ev.currentTarget.offsetLeft;
        this.filmStripScrollLeft = ev.currentTarget.scrollLeft;
        this.formerTarget = ev.target;
        this.filmStripMoved = false;
    },
    _onMouseLeave: function (ev) {
        if (!this.filmStripIsDown) {
            return;
        }
        ev.currentTarget.classList.remove('activeDrag');
        this.filmStripIsDown = false
    },
    _onMouseUp: function (ev) {
        this.filmStripIsDown = false;
        ev.currentTarget.classList.remove('activeDrag');
    },
    _onMouseMove: function (ev) {
        if (!this.filmStripIsDown) {
            return;
        }
        ev.preventDefault();
        ev.currentTarget.classList.add('activeDrag');
        this.filmStripMoved = true;
        const x = ev.pageX - ev.currentTarget.offsetLeft;
        const walk = (x - this.filmStripStartX) * 2;
        ev.currentTarget.scrollLeft = this.filmStripScrollLeft - walk;
    },
    _onClickHandler: function(ev) {
        if(this.filmStripMoved) {
            ev.stopPropagation();
            ev.preventDefault();
        }
    },
    _applyHash: function () {
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
    },

    /**
     * Sets the url hash from the selected product options.
     *
     * @private
     */
    _setUrlHash: function ($parent) {
        const inputs = document.querySelectorAll(
            'input.js_variant_change:checked, select.js_variant_change option:checked'
        );
        let attributeIds = [];
        inputs.forEach((element) => attributeIds.push(element.dataset.attributeValueId));
        if (attributeIds.length > 0) {
            // Avoid adding new entries in session history by replacing the current one
            history.replaceState(null, '', '#attribute_values=' + attributeIds.join(','));
        }
    },
    /**
     * Set the checked values active.
     *
     * @private
     * @param {Array} valueSelectors Selectors
     */
    _changeAttribute: function (valueSelectors) {
        valueSelectors.forEach((selector) => {
            $(selector)
                .removeClass("active")
                .filter(":has(input:checked)")
                .addClass("active")
                .find('input')
                .trigger("change");
        });
    },
    _getProductImageLayout: function () {
        return document.querySelector("#product_detail_main").dataset.image_layout;
    },
    _getProductImageWidth: function () {
        return document.querySelector("#product_detail_main").dataset.image_width;
    },
    _getProductImageContainerSelector: function () {
        return {
            'carousel': "#o-carousel-product",
            'grid': "#o-grid-product",
        }[this._getProductImageLayout()];
    },
    _isEditorEnabled() {
        return document.body.classList.contains("editor_enable");
    },
    /**
     * @private
     */
    _startZoom: function () {
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
    },
    _cleanupZoom() {
        if (!this.zoomCleanup || !this.zoomCleanup.length) {
            return;
        }
        for (const cleanup of this.zoomCleanup) {
            cleanup();
        }
        this.zoomCleanup = undefined;
    },
    /**
     * On website, we display a carousel instead of only one image
     *
     * @override
     * @private
     */
    _updateProductImage: function ($productContainer, newImages) {
        let $images = $productContainer.find(this._getProductImageContainerSelector());
        // When using the web editor, don't reload this or the images won't
        // be able to be edited depending on if this is done loading before
        // or after the editor is ready.
        if ($images.length && !this._isEditorEnabled()) {
            const $newImages = $(newImages);
            $images.after($newImages);
            $images.remove();
            $images = $newImages;
            // Update the sharable image (only work for Pinterest).
            const shareImageSrc = $images[0].querySelector('img').src;
            document.querySelector('meta[property="og:image"]')
                .setAttribute('content', shareImageSrc);

            if ($images.attr('id') === 'o-carousel-product') {
                $images.carousel(0);
            }
            this._startZoom();
            // fix issue with carousel height
            this.trigger_up('widgets_start_request', {$target: $images});
        }
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    async _onClickAdd(ev) {
        ev.preventDefault();
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
            return this._getCombinationInfo(ev).then(() => {
                return !(ev.target).closest('.js_product').classList.contains('.css_not_available') ? def() : Promise.resolve();
            });
        }
        return def();
    },
    /**
     * Event handler to increase or decrease quantity from the product page.
     *
     * @private
     * @param {MouseEvent} ev
     *
     * @returns {void}
     */
    _onChangeQuantity: function (ev) {
        ev.preventDefault();

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
    },
    /**
     * Search attribute values based on the input text.
     *
     * @private
     * @param {Event} ev
     */
    _searchAttributeValues(ev) {
        const input = ev.target;
        const searchValue = input.value.toLowerCase();

        document.querySelectorAll(`#${input.dataset.containerId} .form-check`).forEach(item =>{
            const labelText = item.querySelector('.form-check-label').textContent.toLowerCase();
            item.style.display = labelText.includes(searchValue) ? '' : 'none'
        });
    },
    /**
     * Toggle the button text between "View More" and "View Less"
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onToggleViewMoreLabel(ev) {
        const button = ev.target;
        const isExpanded = button.getAttribute('aria-expanded') === 'true';

        button.innerHTML = isExpanded ? "View Less" : "View More";
    },
    /**
     * When the quantity is changed, we need to query the new price of the product.
     * Based on the pricelist, the price might change when quantity exceeds a certain amount.
     *
     * @private
     * @param {MouseEvent} ev
     *
     * @returns {void}
     */
    _onChangeAddQuantity: function (ev) {
        const $parent = $(ev.currentTarget).closest('form');
        if ($parent.length > 0) {
            this.triggerVariantChange($parent);
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onChangeAttribute: function (ev) {
        if (!ev.defaultPrevented) {
            ev.preventDefault();
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
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onSubmitSaleSearch: function (ev) {
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
    },
    /**
     * Toggles the add to cart button depending on the possibility of the
     * current combination.
     *
     * @override
     */
    _toggleDisable: function ($parent, isCombinationPossible) {
        VariantMixin._toggleDisable.apply(this, arguments);
        $parent.find("#add_to_cart").toggleClass('disabled', !isCombinationPossible);
        $parent.find(".o_we_buy_now").toggleClass('disabled', !isCombinationPossible);
    },
    /**
     * Write the properties of the form elements in the DOM to prevent the
     * current selection from being lost when activating the web editor.
     *
     * @override
     */
    onChangeVariant: function (ev) {
        var $component = $(ev.currentTarget).closest('.js_product');
        $component.find('input').each(function () {
            var $el = $(this);
            $el.attr('checked', $el.is(':checked'));
        });
        $component.find('select option').each(function () {
            var $el = $(this);
            $el.attr('selected', $el.is(':selected'));
        });

        this._setUrlHash($component);

        return VariantMixin.onChangeVariant.apply(this, arguments);
    },
    /**
     * @private
     */
    _onClickReviewsLink: function () {
        $('#o_product_page_reviews_content').collapse('show');
    },
    /**
     * Prevent multiclicks on confirm button when the form is submitted
     *
     * @private
     */
    _onClickConfirmOrder: function () {
        // FIXME ANVFE this should only be triggered when we effectively click on that specific button no?
        // should not impact the address page at least
        const submitFormButton = $('form[name="o_wsale_confirm_order"]').find('button[type="submit"]');
        submitFormButton.attr('disabled', true);
        setTimeout(() => submitFormButton.attr('disabled', false), 5000);
    },

    /**
     * Highlight selected color
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onChangeColorAttribute: function (ev) {
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
    },

    _onChangePillsAttribute: function (ev) {
        const radio = ev.target.closest('.o_variant_pills').querySelector("input");
        radio.click();  // Trigger onChangeVariant.
        var $parent = $(ev.target).closest('.js_product');
        $parent.find('.o_variant_pills')
            .removeClass("active border-primary text-primary-emphasis bg-primary-subtle")
            .filter(':has(input:checked)')
            .addClass("active border-primary text-primary-emphasis bg-primary-subtle");
    },

    // -------------------------------------
    // Utils
    // -------------------------------------

    /**
     * Update the root product during based on the form elements.
     *
     * @private
     * @param {HTMLFormElement} form - The form in which the product is.
     *
     * @returns {void}
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
    },

    /**
     * Return the selected stored PTAV(s) of in the provided form.
     *
     * @private
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
    },

    /**
     * Return the custom PTAV(s) values in the provided form.
     *
     * @private
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
    },

    /**
     * Return the selected non-stored PTAV(s) of the product in the provided form.
     *
     * @private
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
    },
});

publicWidget.registry.WebsiteSale = WebsiteSale

export default {
    WebsiteSale: publicWidget.registry.WebsiteSale,
};
