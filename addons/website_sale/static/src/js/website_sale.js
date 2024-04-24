/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import VariantMixin from "@website_sale/js/sale_variant_mixin";
import wSaleUtils from "@website_sale/js/website_sale_utils";
const cartHandlerMixin = wSaleUtils.cartHandlerMixin;
import "@website/libs/zoomodoo/zoomodoo";
import {extraMenuUpdateCallbacks} from "@website/js/content/menu";
import { ProductImageViewer } from "@website_sale/js/components/website_sale_image_viewer";
import { rpc } from "@web/core/network/rpc";
import { debounce, throttleForAnimation } from "@web/core/utils/timing";
import { listenSizeChange, SIZES, utils as uiUtils } from "@web/core/ui/ui_service";
import { isBrowserFirefox, hasTouch } from "@web/core/browser/feature_detection";
import { Component } from "@odoo/owl";

export const WebsiteSale = publicWidget.Widget.extend(VariantMixin, cartHandlerMixin, {
    selector: '.oe_website_sale',
    events: Object.assign({}, VariantMixin.events || {}, {
        'change form .js_product:first input[name="add_qty"]': '_onChangeAddQuantity',
        'mouseup .js_publish': '_onMouseupPublish',
        'touchend .js_publish': '_onMouseupPublish',
        'change .oe_cart input.js_quantity[data-product-id]': '_onChangeCartQuantity',
        'click .oe_cart a.js_add_suggested_products': '_onClickSuggestedProduct',
        'click a.js_add_cart_json': '_onClickAddCartJSON',
        'click .a-submit': '_onClickSubmit',
        'change form.js_attributes input, form.js_attributes select': '_onChangeAttribute',
        'mouseup form.js_add_cart_json label': '_onMouseupAddCartLabel',
        'touchend form.js_add_cart_json label': '_onMouseupAddCartLabel',
        'submit .o_wsale_products_searchbar_form': '_onSubmitSaleSearch',
        'click .toggle_summary': '_onToggleSummary',
        'click #add_to_cart, .o_we_buy_now, #products_grid .o_wsale_product_btn .a-submit': 'async _onClickAdd',
        'click input.js_product_change': 'onChangeVariant',
        'change .js_main_product [data-attribute_exclusions]': 'onChangeVariant',
        'change oe_advanced_configurator_modal [data-attribute_exclusions]': 'onChangeVariant',
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

        this._changeCartQuantity = debounce(this._changeCartQuantity.bind(this), 500);

        this.isWebsite = true;
        this.filmStripStartX = 0;
        this.filmStripIsDown = false;
        this.filmStripScrollLeft = 0;
        this.filmStripMoved = false;

        delete this.events['change .main_product:not(.in_cart) input.js_quantity'];
        delete this.events['change [data-attribute_exclusions]'];
    },
    /**
     * @override
     */
    start() {
        const def = this._super(...arguments);

        this._applyHashFromSearch();

        this.el.querySelectorAll("div.js_product").forEach((product) => {
            const productChangeEL = product.querySelector('input.js_product_change')
            productChangeEL?.dispatchEvent(new Event('change'));
        });

        // This has to be triggered to compute the "out of stock" feature and the hash variant changes
        this.triggerVariantChange(this.el);

        listenSizeChange(() => {
            if (uiUtils.getSize() === SIZES.XL) {
                this.el.querySelectorAll('.toggle_summary_div').forEach(el => el.classList.add('d-none d-xl-block'));
            }
        })

        this._startZoom();

        window.addEventListener('popstate', (ev) => {
            if (ev.state?.newURL) {
                this._applyHash();
                this.triggerVariantChange(this.el);
            }
        });

        // This allows conditional styling for the filmstrip
        if (isBrowserFirefox() || hasTouch()) {
            this.el.querySelector('.o_wsale_filmstip_container')?.classList.add('o_wsale_filmstip_fancy_disabled');
        }

        this.getRedirectOption();
        return def;
    },
    destroy() {
        this._super.apply(this, arguments);
        this._cleanupZoom();
    },
    /**
     * The selector is different when using list view of variants.
     *
     * @override
     */
    getSelectedVariantValues: function (container) {
        const combination = container?.querySelector('input.js_product_change:checked')?.dataset.combination;

        if (combination) {
            return combination;
        }
        return VariantMixin.getSelectedVariantValues.apply(this, arguments);
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
        if (params.get("attr")) {
            var attributeIds = params.get("attr").split(',');
            var inputs = this.el.querySelectorAll('input.js_variant_change, select.js_variant_change option');
            attributeIds.forEach((id) => {
                var toSelect = [...inputs].filter(input => input.dataset.valueId == id);;
                if (toSelect.tagName === 'INPUT' && toSelect.type === 'radio') {
                    toSelect.prop('checked', true);
                } else if (toSelect.tagName === 'OPTION') {
                    toSelect.prop('selected', true);
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
    _setUrlHash: function (parent) {
        const attributes = parent.querySelectorAll('input.js_variant_change:checked', 'select.js_variant_change option:selected');
        if (!attributes.length) {
            return;
        }
        const attributeIds = [...attributes].map((elem) => elem.dataset.valueId);
        window.location.replace('#attr=' + attributeIds.join(','));
    },
    /**
     * Set the checked values active.
     *
     * @private
     * @param {Array} valueSelectors Selectors
     */
    _changeAttribute: function (valueSelectors) {
        valueSelectors.forEach((selector) => {
            const el = document.querySelector(selector);
            el?.classList.remove("active")
            if (el?.querySelector("input:checked")) {
                el.classList.add("active");
            }
        });
    },
    /**
     * @private
     */
    _changeCartQuantity: function (input, value, dom_optional, line_id, productIDs) {
        debugger;
        [...dom_optional].forEach((elem) => {
            elem.querySelector('.js_quantity').textContent = value;
            productIDs.push(elem.querySelector('span[data-product-id]').dataset.productId);
        });
        input.dataset.updateChange = 'true';

        rpc("/shop/cart/update_json", {
            line_id: line_id,
            product_id: parseInt(input.dataset.productId, 10),
            set_qty: value,
            display: true,
        }).then((data) => {
            input.dataset.updateChange = 'false';
            let check_value = parseInt(input.value || 0, 10);
            if (isNaN(check_value)) {
                check_value = 1;
            }
            if (value !== check_value) {
                input.dispatchEvent(new Event('change'));
                return;
            }
            if (!data.cart_quantity) {
                return window.location = '/shop/cart';
            }
            input.value = data.quantity;
            this.document.querySelector('.js_quantity[data-line-id='+line_id+']').value = data.quantity;
            this.document.querySelector('.js_quantity[data-line-id='+line_id+']').textContent = data.quantity;

            wSaleUtils.updateCartNavBar(data);
            wSaleUtils.showWarning(data.notification_info.warning);
            // Propagating the change to the express checkout forms
            Component.env.bus.trigger('cart_amount_changed', [data.amount, data.minor_amount]);
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
    _getProductId: function (parent) {
        if (parent.querySelector('input.js_product_change')) {
            return parseInt(parent.querySelector('input.js_product_change:checked').value);
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
        // Do not activate image zoom on hover for mobile devices
        const salePage = document.querySelector(".o_wsale_product_page");
        if (!salePage || uiUtils.isSmall() || this._getProductImageWidth() === "none") {
            return;
        }
        this._cleanupZoom();
        this.zoomCleanup = [];
        // Zoom on hover
        if (salePage.dataset.ecomZoomAuto) {
            const images = salePage.querySelectorAll("img[data-zoom]");
            for (const image of images) {
                const callback = () => {
                    image.zoomOdoo({
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
                    const zoomOdoo = image.dataset.zoomOdoo;
                    if (zoomOdoo) {
                        zoomOdoo.hide();
                        image.removeEventListener();
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
    _updateProductImage: function (productContainer, displayImage, productId, productTemplateId, newImages, isCombinationPossible) {
        let images = productContainer.querySelectorAll(this._getProductImageContainerSelector());
        // When using the web editor, don't reload this or the images won't
        // be able to be edited depending on if this is done loading before
        // or after the editor is ready.
        if (images && !this._isEditorEnabled()) {
            const parser = new DOMParser();
            newImages = parser.parseFromString(newImages, 'text/html').querySelector('#o-carousel-product');
            images[0].parentNode.appendChild(newImages);
            images.forEach((img) => img.remove());
            images = newImages;
            // Update the sharable image (only work for Pinterest).
            const shareImageSrc =  images.querySelector('img').src;
            document.querySelector('meta[property="og:image"]')
                .setAttribute('content', shareImageSrc);

            if (images.getAttribute('id') === 'o-carousel-product') {
                // TODO-VISP take a look
                new Carousel(images, {interval: 0});
            }
            this._startZoom();
            // fix issue with carousel height
            this.trigger_up('widgets_start_request', {target: images});
        }
        images.classList.toggle('css_not_available', !isCombinationPossible);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAdd: function (ev) {
        ev.preventDefault();
        const def = () => {
            this.getCartHandlerOptions(ev);
            return this._handleAdd(ev.currentTarget.closest('form'));
        };
        if (this.el.querySelector('.js_add_cart_variants').children.length) {
            return this._getCombinationInfo(ev).then(() => {
                return !ev.target.closest('.js_product').classList.contains("css_not_available") ? def() : Promise.resolve();
            });
        }
        return def();
    },
    /**
     * Initializes the optional products modal
     * and add handlers to the modal events (confirm, back, ...)
     *
     * @private
     * @param {Element} form the related webshop form
     */
    _handleAdd: function (form) {
        const self = this;
        this.form = form;

        const productSelector = [
            'input[type="hidden"][name="product_id"]',
            'input[type="radio"][name="product_id"]:checked'
        ];

        const productReady = this.selectOrCreateProduct(
            form,
            parseInt(form.querySelector(productSelector.join(', ')).value, 10),
            form.querySelector('.product_template_id').value,
        );

        return productReady.then(function (productId) {
            form.querySelector(productSelector.join(', ')).value = productId;
            self._updateRootProduct(form, productId);
            return self._onProductReady();
        });
    },

    _onProductReady: function () {
        return this._submitForm();
    },

    /**
     * Add custom variant values and attribute values that do not generate variants
     * in the params to submit form if 'stay on page' option is disabled, or call
     * '_addToCartInPage' otherwise.
     *
     * @private
     * @returns {Promise}
     */
    _submitForm: function () {
        const params = this.rootProduct;

        const product = document.querySelector('#product_detail');
        const productTrackingInfo = product.dataset.productTrackingInfo;
        if (productTrackingInfo) {
            productTrackingInfo.quantity = params.quantity;
            product.dispatchEvent( new CustomEvent('add_to_cart_event', {detail: [productTrackingInfo]}));
        }

        params.add_qty = params.quantity;
        params.product_custom_attribute_values = JSON.stringify(params.product_custom_attribute_values);
        params.no_variant_attribute_values = JSON.stringify(params.no_variant_attribute_values);
        delete params.quantity;
        return this.addToCart(params);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAddCartJSON: function (ev) {
        this.onClickAddCartJSON(ev);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onChangeAddQuantity: function (ev) {
        this.onChangeAddQuantity(ev);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onMouseupPublish: function (ev) {
        ev.currentTarget.parents('.thumbnail').forEach((elem) => {
            elem.classList.toggle('disabled');
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onChangeCartQuantity: function (ev) {
        debugger;
        const input = ev.currentTarget;
        if (input.dataset.updateChange) {
            return;
        }
        let value = parseInt(input.value || 0, 10);
        if (isNaN(value)) {
            value = 1;
        }
        const dom = input.closest('tr');
        // var default_price = parseFloat($dom.find('.text-danger > span.oe_currency_value').text());
        let dom_optional = [];
        let sibling = dom.nextElementSibling;
        while (sibling && sibling.classList.contains('optional_product') && sibling.classList.contains('info')) {
            dom_optional.push(sibling);
            sibling = sibling.nextElementSibling;
        }
        const line_id = parseInt(input.dataset.line_id, 10);
        const productIDs = [parseInt(input.dataset.productId, 10)];
        this._changeCartQuantity(input, value, dom_optional, line_id, productIDs);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickSuggestedProduct: function (ev) {
        let inputElement = ev.currentTarget.previousElementSibling;
        if (inputElement && inputElement.tagName === 'INPUT') {
            inputElement.value = 1;
            inputElement.dispatchEvent(new Event('change'));
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickSubmit: function (ev, forceSubmit) {
        if (ev.currentTarget.matches('#add_to_cart, #products_grid .a-submit') && !forceSubmit) {
            return;
        }
        var aSubmit = ev.currentTarget;
        if (!ev.isDefaultPrevented() && !aSubmit.classList.contains("disabled")) {
            ev.preventDefault();
            aSubmit.closest('form').submit();
        }
        if (aSubmit.classList.contains('a-submit-disable')) {
            aSubmit.classList.add("disabled");
        }
        if (aSubmit.classList.contains('a-submit-loading')) {
            const loadingEl = document.createElement('SPAN');
            loadingEl.className = "fa fa-cog fa-spin";

            const fa_span = aSubmit.querySelector('span[class*="fa"]');
            if (fa_span) {
                fa_span.replaceWith(loadingEl);
            } else {
                aSubmit.append(loadingEl);
            }
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onChangeAttribute: function (ev) {
        if (!ev.isDefaultPrevented()) {
            ev.preventDefault();
            const productGrid = this.el.querySelector(".o_wsale_products_grid_table_wrapper");
            if (productGrid) {
                productGrid.classList.add("opacity-50");
            }
            ev.currentTarget.closest("form").submit();
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onMouseupAddCartLabel: function (ev) { // change price when they are variants
        const label = ev.currentTarge;
        const price = label.closest("form").querySelector(".oe_price .oe_currency_value");
        if (!price.dataset.price) {
            price.dataset.price = parseFloat(price.textContent);
        }
        const value = price.dataset.price + parseFloat(label.querySelector(".badge span").textContent || 0);

        const dec = value % 1;
        price.innerHTML = value + (dec < 0.01 ? ".00" : (dec < 1 ? "0" : "") );
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onSubmitSaleSearch: function (ev) {
        if (!this.el.querySelector('.dropdown_sorty_by').length) {
            return;
        }
        const target = ev.currentTarget;
        if (!ev.isDefaultPrevented() && !target.classList.contains("disabled")) {
            ev.preventDefault();
            let oldurl = target.getAttribute('action');
            oldurl += (oldurl.indexOf("?")===-1) ? "?" : "";
            if (target.querySelector('[name=noFuzzy]').value === "true") {
                oldurl += '&noFuzzy=true';
            }
            const search = target.querySelector('input.search-query');
            window.location = oldurl + '&' + search.getAttribute('name') + '=' + encodeURIComponent(search.value);
        }
    },
    /**
     * Toggles the add to cart button depending on the possibility of the
     * current combination.
     *
     * @override
     */
    _toggleDisable: function (parent, isCombinationPossible) {
        VariantMixin._toggleDisable.apply(this, arguments);
        parent.querySelector("#add_to_cart").classList.toggle('disabled', !isCombinationPossible);
        parent.querySelector(".o_we_buy_now")?.classList.toggle('disabled', !isCombinationPossible);
    },
    /**
     * Write the properties of the form elements in the DOM to prevent the
     * current selection from being lost when activating the web editor.
     *
     * @override
     */
    onChangeVariant: function (ev) {
        const component = ev.currentTarget.closest('.js_product');
        component.querySelectorAll('input').forEach(() => {
            this.el.setAttribute('checked', this.el.checked);
        });
        component.querySelectorAll('select option').forEach(() => {
            this.el.setAttribute('selected', this.el.selected);
        });

        this._setUrlHash(component);

        return VariantMixin.onChangeVariant.apply(this, arguments);
    },
    /**
     * @private
     */
    _onToggleSummary: function () {
        this.el.querySelectorAll('.toggle_summary_div').forEach(element => {
            element.classList.toggle('d-none');
            element.classList.remove('d-xl-block');
        });
    },
    /**
     * @private
     */
    _applyHashFromSearch() {
        const params =  new URL(window.location).searchParams;
        if (params.get("attrib")) {
            const dataValueIds = [];
            for (const attrib of [].concat(params.get("attrib"))) {
                const attribSplit = attrib.split('-');
                const attribValueSelector = `.js_variant_change[name="ptal-${attribSplit[0]}"][value="${attribSplit[1]}"]`;
                const attribValue = this.el.querySelector(attribValueSelector);
                if (attribValue !== null) {
                    dataValueIds.push(attribValue.dataset.value_id);
                }
            }
            if (dataValueIds.length) {
                window.location.hash = `attr=${dataValueIds.join(',')}`;
            }
        }
        this._applyHash();
    },
    /**
     * @private
     */
    _onClickReviewsLink: function () {
        const collapse = new Collapse(this.el.querySelector('#o_product_page_reviews_content'));
        collapse.show();
    },
    /**
     * Prevent multiclicks on confirm button when the form is submitted
     *
     * @private
     */
    _onClickConfirmOrder: function () {
        const submitFormButton = this.el.querySelector('form[name="o_wsale_confirm_order"]')?.querySelector('button[type="submit"]');
        if (submitFormButton) {
            submitFormButton.setAttribute('disabled', true);
            setTimeout(() => submitFormButton.setAttribute('disabled', false), 5000);
        }
    },

    // -------------------------------------
    // Utils
    // -------------------------------------
    /**
     * Update the root product during an Add process.
     *
     * @private
     * @param {Object} form
     * @param {Number} productId
     */
    _updateRootProduct(form, productId) {
        this.rootProduct = {
            product_id: productId,
            quantity: parseFloat(form.querySelector('input[name="add_qty"]').value || 1),
            product_custom_attribute_values: this.getCustomVariantValues(form.querySelector('.js_product')),
            variant_values: this.getSelectedVariantValues(form.querySelector('.js_product')),
            no_variant_attribute_values: this.getNoVariantAttributeValues(form.querySelector('.js_product'))
        };
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
        var clickedValue = ev.target.value;
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

        var grid = this.el.querySelector('#products_grid');
        // Disable transition on all list elements, then switch to the new
        // layout then reenable all transitions after having forced a redraw
        // TODO should probably be improved to allow disabling transitions
        // altogether with a class/option.
        grid.querySelectorAll('*').forEach(gridEls => {
            gridEls.style.transition = 'none';
        });
        grid.classList.toggle('o_wsale_layout_list', isList);
        void grid.offsetWidth;
        grid.querySelectorAll('*').forEach(gridEls => {
            gridEls.style.transition = '';
        });
        if (wysiwyg) {
            wysiwyg.odooEditor.observerActive('_onApplyShopLayoutChange');
        }
    },
});


publicWidget.registry.websiteSaleCarouselProduct = publicWidget.Widget.extend({
    selector: '#o-carousel-product',
    disabledInEditableMode: false,
    events: {
        'wheel .o_carousel_product_indicators': '_onMouseWheel',
    },

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this._updateCarouselPosition();
        this.throttleOnResize = throttleForAnimation(this._onSlideCarouselProduct.bind(this));
        extraMenuUpdateCallbacks.push(this._updateCarouselPosition.bind(this));
        if (this.el.querySelector('.carousel-indicators')?.length > 0) {
            this.el.addEventListener('slide.bs.carousel.carousel_product_slider', this._onSlideCarouselProduct.bind(this));
            window.addEventListener('resize.carousel_product_slider', this.throttleOnResize);
            this._updateJustifyContent();
        }
    },
    /**
     * @override
     */
    destroy() {
        this.el.style.top = '';
        this.el.removeEventListener('slide.bs.carousel.carousel_product_slider', this._onSlideCarouselProduct.bind(this));
        window.removeEventListener('resize.carousel_product_slider', this.throttleOnResize);
        if (this.throttleOnResize) {
            this.throttleOnResize.cancel();
        }
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _updateCarouselPosition() {
        let size = 5;
        for (const el of document.querySelectorAll('.o_top_fixed_element')) {
            size += el.style.outerHeight;
        }
        this.el.style.top = size;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Center the selected indicator to scroll the indicators list when it
     * overflows.
     *
     * @private
     * @param {Event} ev
     */
    _onSlideCarouselProduct: function (ev) {
        const isReversed = getComputedStyle(this.el).flexDirection === "column-reverse";
        const isLeftIndicators = this.el.classList.contains('o_carousel_product_left_indicators');
        const indicatorsDiv = isLeftIndicators ? this.el.querySelectorAll('.o_carousel_product_indicators') : this.el.querySelectorAll('.carousel-indicators');
        let indicatorIndex = Array.from(ev.relatedTarget.parentNode.children).indexOf(ev.relatedTarget)
        indicatorIndex = indicatorIndex > -1 ? indicatorIndex : Array.from(this.el.querySelectorAll('li')).indexOf(this.el.querySelector('li.active'))
        const indicator = indicatorsDiv.querySelector('[data-bs-slide-to=' + indicatorIndex + ']');
        const indicatorsDivSize = isLeftIndicators && !isReversed ? indicatorsDiv.offsetHeight : indicatorsDiv.offsetWidth;
        const indicatorSize = isLeftIndicators && !isReversed ? indicator.offsetHeight : indicator.offsetWidth;
        const indicatorPosition = isLeftIndicators && !isReversed ? indicator.offsetTop : indicator.offsetLeft;
        const scrollSize = isLeftIndicators && !isReversed ? indicatorsDiv.scrollHeight : indicatorsDiv.scrollWidth;
        let indicatorsPositionDiff = (indicatorPosition + (indicatorSize/2)) - (indicatorsDivSize/2);
        indicatorsPositionDiff = Math.min(indicatorsPositionDiff, scrollSize - indicatorsDivSize);
        this._updateJustifyContent();
        const indicatorsPositionX = isLeftIndicators && !isReversed ? '0' : '-' + indicatorsPositionDiff;
        const indicatorsPositionY = isLeftIndicators && !isReversed ? '-' + indicatorsPositionDiff : '0';
        const translate3D = indicatorsPositionDiff > 0 ? "translate3d(" + indicatorsPositionX + "px," + indicatorsPositionY + "px,0)" : '';
        indicatorsDiv.style.transform = translate3D;
    },
    /**
     * @private
     */
     _updateJustifyContent: function () {
        const indicatorsDiv = this.el.querySelector('.carousel-indicators');
        indicatorsDiv.style.justifyContent = 'start';
        if (uiUtils.getSize() <= SIZES.MD) {
            const lastChild = indicatorsDiv.lastElementChild;
            const liWidth = this.el.querySelector('li').offsetWidth;
            if ((lastChild.offsetLeft + liWidth) < indicatorsDiv.offsetWidth) {
                indicatorsDiv.style.justifyContent = 'center';
            }
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onMouseWheel: function (ev) {
        ev.preventDefault();
        const carousel = new Carousel(this.el);
        if (ev.originalEvent.deltaY > 0) {
        // TODO VISP: remove this when the carousel is fixed
            carousel.next();
        } else {
            carousel.prev();
        }
    },
});

publicWidget.registry.websiteSaleProductPageReviews = publicWidget.Widget.extend({
    selector: '#o_product_page_reviews',
    disabledInEditableMode: false,

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this._updateChatterComposerPosition();
        extraMenuUpdateCallbacks.push(this._updateChatterComposerPosition.bind(this));
    },
    /**
     * @override
     */
    destroy() {
        this.el.querySelector('.o_portal_chatter_composer').style.top = '';
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
            size += el.offsetHeight;
        }
        this.el.querySelector('.o_portal_chatter_composer').style.top = size;
    },
});

export default {
    WebsiteSale: publicWidget.registry.WebsiteSale,
    WebsiteSaleLayout: publicWidget.registry.WebsiteSaleLayout,
    WebsiteSaleCarouselProduct: publicWidget.registry.websiteSaleCarouselProduct,
    WebsiteSaleProductPageReviews: publicWidget.registry.websiteSaleProductPageReviews,
};
