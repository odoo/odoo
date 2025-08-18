import { hasTouch, isBrowserFirefox } from "@web/core/browser/feature_detection";
import { rpc } from "@web/core/network/rpc";
import { utils as uiUtils } from "@web/core/ui/ui_service";
import publicWidget from "@web/legacy/js/public/public_widget";
import "@website/libs/zoomodoo/zoomodoo";
import { ProductImageViewer } from "@website_sale/js/components/website_sale_image_viewer";
import VariantMixin from "@website_sale/js/sale_variant_mixin";


export const WebsiteSale = publicWidget.Widget.extend(VariantMixin, {
    selector: '.oe_website_sale',
    events: Object.assign({}, VariantMixin.events || {}, {
        'change form .js_product:first input[name="add_qty"]': '_onChangeAddQuantity',
        'click a.js_add_cart_json': '_onChangeQuantity',
        'click .a-submit': '_onClickSubmit',
        'change form.js_attributes input, form.js_attributes select': '_onChangeAttribute',
        'submit .o_wsale_products_searchbar_form': '_onSubmitSaleSearch',
        'click #add_to_cart, .o_we_buy_now, #products_grid .o_wsale_product_btn .a-submit': '_onClickAdd',
        'click input.js_product_change': 'onChangeVariant',
        'change .js_main_product [data-attribute_exclusions]': 'onChangeVariant',
        'click .o_product_page_reviews_link': '_onClickReviewsLink',
        'mousedown .o_wsale_filmstip_wrapper': '_onMouseDown',
        'mouseleave .o_wsale_filmstip_wrapper': '_onMouseLeave',
        'mouseup .o_wsale_filmstip_wrapper': '_onMouseUp',
        'mousemove .o_wsale_filmstip_wrapper': '_onMouseMove',
        'click .o_wsale_filmstip_wrapper' : '_onClickHandler',
        'submit': '_onClickConfirmOrder',
    }),

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
        const filmstripContainer = this.el.querySelector('.o_wsale_filmstip_container');
        const filmstripContainerWidth = filmstripContainer
            ? filmstripContainer.getBoundingClientRect().width : 0;
        const filmstripWrapper = this.el.querySelector('.o_wsale_filmstip_wrapper');
        const filmstripWrapperWidth = filmstripWrapper
            ? filmstripWrapper.getBoundingClientRect().width : 0;
        const isFilmstripScrollable = filmstripWrapperWidth < filmstripContainerWidth
        if (isBrowserFirefox() || hasTouch() || isFilmstripScrollable) {
            filmstripContainer?.classList.add('o_wsale_filmstip_fancy_disabled');
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
            $(selector).removeClass("active").filter(":has(input:checked)").addClass("active");
        });
    },
    /**
     * This is overridden to handle the "List View of Variants" of the web shop.
     * That feature allows directly selecting the variant from a list instead of selecting the
     * attribute values.
     *
     * Since the layout is completely different, we need to fetch the product_id directly
     * from the selected variant.
     *
     * @override
     */
    _getProductId: function ($parent) {
        if ($parent.find('input.js_product_change').length !== 0) {
            return parseInt($parent.find('input.js_product_change:checked').val());
        }
        else {
            return VariantMixin._getProductId.apply(this, arguments);
        }
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
    _getProductImageContainer: function () {
        return document.querySelector(this._getProductImageContainerSelector());
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
            const images = this.el.querySelectorAll('img[data-zoom]');
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
            const images = this.el.querySelectorAll('.product_detail_img');
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
    _updateProductImage: function ($productContainer, displayImage, productId, productTemplateId, newImages, isCombinationPossible) {
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
        $images.toggleClass('css_not_available', !isCombinationPossible);
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
            return this.call('cart', 'add', this.rootProduct, {
                isBuyNow: isBuyNow,
                isConfigured: isConfigured,
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
            ev.currentTarget.querySelector('i').classList.contains('fa-minus') ? -1 : 1
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
    _onClickSubmit: function (ev) {
        if ($(ev.currentTarget).is('#add_to_cart, #products_grid .a-submit')) {
            return;
        }
        var $aSubmit = $(ev.currentTarget);
        if (!ev.defaultPrevented && !$aSubmit.is(".disabled")) {
            ev.preventDefault();
            $aSubmit.closest('form').submit();
        }
        if ($aSubmit.hasClass('a-submit-disable')) {
            $aSubmit.addClass("disabled");
        }
        if ($aSubmit.hasClass('a-submit-loading')) {
            var loading = '<span class="fa fa-cog fa-spin"/>';
            var fa_span = $aSubmit.find('span[class*="fa"]');
            if (fa_span.length) {
                fa_span.replaceWith(loading);
            } else {
                $aSubmit.append(loading);
            }
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
            $(ev.currentTarget).closest("form").submit();
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
        const productId = parseInt(form.querySelector([
            'input[type="hidden"][name="product_id"]',
            // Variants list view
            'input[type="radio"][name="product_id"]:checked',
        ].join(','))?.value);
        const quantity = parseFloat(form.querySelector('input[name="add_qty"]')?.value);
        const isCombo = form.querySelector(
            'input[type="hidden"][name="product_type"]'
        )?.value === 'combo';
        this.rootProduct = {
            ...(productId ? {productId: productId} : {}),
            productTemplateId: parseInt(form.querySelector(
                'input[type="hidden"][name="product_template_id"]',
            ).value),
            ...(quantity ? {quantity: quantity} : {}),
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
        // Variants list view
        let combination = form.querySelector('input.js_product_change:checked')?.dataset.combination;
        if (combination) {
            return JSON.parse(combination);
        }

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

publicWidget.registry.WebsiteSaleLayout = publicWidget.Widget.extend({
    selector: '.oe_website_sale',
    disabledInEditableMode: false,
    events: {
        'change .o_wsale_apply_layout input': '_onApplyShopLayoutChange',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onApplyShopLayoutChange: function (ev) {
        const wysiwyg = this.options.wysiwyg;
        if (wysiwyg) {
            wysiwyg.odooEditor.observerUnactive('_onApplyShopLayoutChange');
        }
        var clickedValue = $(ev.target).val();
        var isList = clickedValue === 'list';
        if (!this.editableMode) {
            rpc('/shop/save_shop_layout_mode', {
                'layout_mode': isList ? 'list' : 'grid',
            });
        }

        const activeClasses = ev.target.parentElement.dataset.activeClasses.split(' ');
        ev.target.parentElement.querySelectorAll('.btn').forEach((btn) => {
            activeClasses.map(c => btn.classList.toggle(c));
        });

        var $grid = this.$('#products_grid');
        // Disable transition on all list elements, then switch to the new
        // layout then reenable all transitions after having forced a redraw
        // TODO should probably be improved to allow disabling transitions
        // altogether with a class/option.
        $grid.find('*').css('transition', 'none');
        $grid.toggleClass('o_wsale_layout_list', isList);
        void $grid[0].offsetWidth;
        $grid.find('*').css('transition', '');
        if (wysiwyg) {
            wysiwyg.odooEditor.observerActive('_onApplyShopLayoutChange');
        }
    },
});

publicWidget.registry.WebsiteSaleAccordionProduct = publicWidget.Widget.extend({
    selector: "#product_accordion",

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this._updateAccordionActiveItem();
    },

    /**
     * Replace the .SCSS styling applied awaiting Js for the default bootstrap classes,
     * opening the first accordion entry and restoring flush behavior.
     *
     * @private
     */
    _updateAccordionActiveItem() {
        const firstAccordionItemEl = this.el.querySelector('.accordion-item');
        if (!firstAccordionItemEl) return;

        const firstAccordionItemButtonEl = firstAccordionItemEl.querySelector('.accordion-button');
        firstAccordionItemButtonEl.classList.remove('collapsed');
        firstAccordionItemButtonEl.setAttribute('aria-expanded', 'true');
        firstAccordionItemEl.querySelector('.accordion-collapse').classList.add('show');
        this.target.classList.remove('o_accordion_not_initialized');
    },
});

publicWidget.registry.websiteSaleProductPageReviews = publicWidget.Widget.extend({
    selector: '#o_product_page_reviews',
    disabledInEditableMode: false,

    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.website_menus = this.bindService("website_menus");
    },

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this._updateChatterComposerPosition();
        this.website_menus.registerCallback(this._updateChatterComposerPosition.bind(this));
        const reviewsContent = this.el.querySelector("#o_product_page_reviews_content");
        const reviewsTitle = this.el.querySelector(".o_product_page_reviews_title");
        reviewsTitle.classList.toggle("collapsed", !reviewsContent.classList.contains("show"));
    },
    /**
     * @override
     */
    destroy() {
        this.$el.find('.o_portal_chatter_composer').css('top', '');
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _updateChatterComposerPosition() {
        let size = 20;
        for (const el of document.querySelectorAll('.o_top_fixed_element')) {
            size += $(el).outerHeight();
        }
        this.$el.find('.o_portal_chatter_composer').css('top', size);
    },
});

export default {
    WebsiteSale: publicWidget.registry.WebsiteSale,
    WebsiteSaleLayout: publicWidget.registry.WebsiteSaleLayout,
    WebsiteSaleProductPage: publicWidget.registry.WebsiteSaleAccordionProduct,
    WebsiteSaleCarouselProduct: publicWidget.registry.websiteSaleCarouselProduct,
    WebsiteSaleProductPageReviews: publicWidget.registry.websiteSaleProductPageReviews,
};
