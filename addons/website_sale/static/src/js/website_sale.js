import { hasTouch, isBrowserFirefox } from "@web/core/browser/feature_detection";
import { rpc } from "@web/core/network/rpc";
import { SIZES, utils as uiUtils } from "@web/core/ui/ui_service";
import { throttleForAnimation } from "@web/core/utils/timing";
import publicWidget from "@web/legacy/js/public/public_widget";
import { extraMenuUpdateCallbacks } from "@website/js/content/menu";
import { zoomOdoo } from "@website/libs/zoomodoo/zoomodoo";
import { ProductImageViewer } from "@website_sale/js/components/website_sale_image_viewer";
import VariantMixin from "@website_sale/js/sale_variant_mixin";
import { cartHandlerMixin } from "@website_sale/js/website_sale_utils";
import { redirect } from "@web/core/utils/urls";

export const WebsiteSale = publicWidget.Widget.extend(VariantMixin, cartHandlerMixin, {
    selector: '.oe_website_sale',
    events: Object.assign({}, VariantMixin.events || {}, {
        'change form .js_product:first input[name="add_qty"]': '_onChangeAddQuantity',
        'click a.js_add_cart_json': '_onClickAddCartJSON',
        'click .a-submit': '_onClickSubmit',
        'change form.js_attributes input, form.js_attributes select': '_onChangeAttribute',
        'mouseup form.js_add_cart_json label': '_onMouseupAddCartLabel',
        'touchend form.js_add_cart_json label': '_onMouseupAddCartLabel',
        'submit .o_wsale_products_searchbar_form': '_onSubmitSaleSearch',
        'click #add_to_cart, .o_we_buy_now, #products_grid .o_wsale_product_btn .a-submit': 'async _onClickAdd',
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
        this.triggerVariantChange(this.el);

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
    getSelectedVariantValues(container) {
        const checkedJsProductEl = container?.querySelector("input.js_product_change:checked");
        const combination = checkedJsProductEl ? checkedJsProductEl.dataset.combination : "";
        if (combination) {
            return JSON.parse(combination);
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
    _setUrlHash(parent) {
        const inputs = document.querySelectorAll(
            'input.js_variant_change:checked, select.js_variant_change option:checked'
        );
        let attributeIds = [];
        inputs.forEach((element) => attributeIds.push(element.dataset.attributeValueId));
        if (attributeIds.length > 0) {
            window.location.hash = `attribute_values=${attributeIds.join(',')}`;
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
            const els = document.querySelectorAll(selector);
            els.forEach((el) => {
                el.classList.remove("active");
                if (el.querySelector("input:checked")) {
                    el.classList.add("active");
                }
            });
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
    _getProductId(parentEl) {
        if (parentEl?.querySelector("input.js_product_change")) {
            return parseInt(parentEl.querySelector("input.js_product_change:checked").value);
        } else {
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
            const images = salePage.querySelectorAll("img[data-zoom]");
            for (const image of images) {
                const callback = () => {
                    if (typeof zoomOdoo !== "object") {
                        zoomOdoo(image, {
                            event: "mouseenter",
                            attach: this._getProductImageContainerSelector(),
                            preventClicks: salePage.dataset.ecomZoomClick,
                            attachToTarget: this._getProductImageLayout() === "grid",
                        });
                    }
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
    _updateProductImage(productContainerEl, displayImage, productId, productTemplateId, newImages, isCombinationPossible) {
        let imagesEl = productContainerEl.querySelector(this._getProductImageContainerSelector());
        // When using the web editor, don't reload this or the images won't
        // be able to be edited depending on if this is done loading before
        // or after the editor is ready.
        if (imagesEl && !this._isEditorEnabled()) {
            const parser = new DOMParser();
            newImages = parser
                .parseFromString(newImages, "text/html")
                .querySelector("#o-carousel-product");
            if (newImages) {
                imagesEl.parentNode.replaceChild(newImages, imagesEl);
                imagesEl = newImages;
                // Update the sharable image (only work for Pinterest).
                const shareImageSrc = imagesEl.querySelector('img').src;
                document.querySelector('meta[property="og:image"]')
                    .setAttribute('content', shareImageSrc);
                if (imagesEl.getAttribute("id") === "o-carousel-product") {
                    window.Carousel.getOrCreateInstance(imagesEl).to(0);
                }
                this._startZoom();
                // fix issue with carousel height
                this.trigger_up("widgets_start_request", { $target: $(imagesEl) });
            }
        }
        imagesEl.classList.toggle("css_not_available", !isCombinationPossible);
    },
    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAdd: function (ev) {
        ev.preventDefault();
        const def = () => {
            this.getCartHandlerOptions(ev);
            return this._handleAdd(ev.currentTarget.closest("form"));
        };
        if (this.el.querySelector(".js_add_cart_variants")?.children.length) {
            return this._getCombinationInfo(ev).then(() => {
                return !ev.target.closest(".js_product").classList.contains("css_not_available")
                    ? def()
                    : Promise.resolve();
            });
        }
        return def();
    },
    /**
     * Initializes the optional products modal
     * and add handlers to the modal events (confirm, back, ...)
     *
     * @private
     * @param {Element} formEl the related webshop form
     */
    _handleAdd(formEl) {
        var self = this;

        var productSelector = [
            'input[type="hidden"][name="product_id"]',
            'input[type="radio"][name="product_id"]:checked',
        ];
        const productTemplateId = parseInt(
            formEl.querySelector('input[type="hidden"][name="product_template_id"]')?.value
        );
        const productReady = this.selectOrCreateProduct(
            formEl,
            parseInt(formEl.querySelector(productSelector.join(", ")).value, 10),
            productTemplateId
        );

        return productReady.then(function (productId) {
            formEl.querySelector(productSelector.join(", ")).value = productId;
            self._updateRootProduct(formEl, productId, productTemplateId);
            return self._onProductReady(formEl.closest(".o_wsale_product_page") !== null);
        });
    },

    _onProductReady(isOnProductPage = false) {
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

        const productEl = document.querySelector("#product_detail");
        let productTrackingInfo;
        if (productEl && productEl.dataset.productTrackingInfo) {
            productTrackingInfo = JSON.parse(productEl.dataset.productTrackingInfo);
        }
        if (productTrackingInfo) {
            productTrackingInfo.quantity = params.quantity;
            productEl.dispatchEvent(
                new CustomEvent("add_to_cart_event", { detail: [productTrackingInfo] })
            );
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
    _onClickSubmit: function (ev) {
        if (ev.currentTarget.matches("#add_to_cart, #products_grid .a-submit")) {
            return;
        }
        var aSubmitEl = ev.currentTarget;
        if (!ev.isDefaultPrevented() && !aSubmitEl.classList.contains("disabled")) {
            ev.preventDefault();
            aSubmitEl.closest("form").submit();
        }
        if (aSubmitEl.classList.contains("a-submit-disable")) {
            aSubmitEl.classList.add("disabled");
        }
        if (aSubmitEl.classList.contains("a-submit-loading")) {
            const loadingEl = document.createElement("SPAN");
            loadingEl.className = "fa fa-cog fa-spin";
            const fa_spanEl = aSubmitEl.querySelector('span[class*="fa"]');
            if (fa_spanEl) {
                fa_spanEl.parentNode.replaceChild(loadingEl, fa_spanEl);
            } else {
                aSubmitEl.append(loadingEl);
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
            ev.currentTarget.closest("form").submit();
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onMouseupAddCartLabel: function (ev) { // change price when they are variants
        const labelEl = ev.currentTarge;
        const priceEl = labelEl.closest("form").querySelector(".oe_price .oe_currency_value");
        if (!priceEl.dataset.price) {
            priceEl.dataset.price = parseFloat(priceEl.textContent);
        }
        const value =
            priceEl.dataset.price + parseFloat(labelEl.querySelector(".badge span").textContent || 0);

        const dec = value % 1;
        priceEl.textContent = value + (dec < 0.01 ? ".00" : dec < 1 ? "0" : "");
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onSubmitSaleSearch: function (ev) {
        if (!this.el.querySelector(".dropdown_sorty_by")) {
            return;
        }
        const targetEl = ev.currentTarget;
        if (!ev.isDefaultPrevented() && !targetEl.classList.contains("disabled")) {
            ev.preventDefault();
            let oldurl = targetEl.getAttribute("action");
            oldurl += (oldurl.indexOf("?")===-1) ? "?" : "";
            if (targetEl.querySelector("[name=noFuzzy]")?.value === "true") {
                oldurl += '&noFuzzy=true';
            }
            const searchEl = targetEl.querySelector("input.search-query");
            const url =
                oldurl +
                "&" +
                searchEl.getAttribute("name") +
                "=" +
                encodeURIComponent(searchEl.value);
            redirect(url);
        }
    },
    /**
     * Toggles the add to cart button depending on the possibility of the
     * current combination.
     *
     * @override
     */
    _toggleDisable(parentEl, isCombinationPossible) {
        VariantMixin._toggleDisable.apply(this, arguments);
        parentEl?.querySelector("#add_to_cart").classList.toggle("disabled", !isCombinationPossible);
        parentEl
            ?.querySelector(".o_we_buy_now")
            ?.classList.toggle("disabled", !isCombinationPossible);
    },
    /**
     * Write the properties of the form elements in the DOM to prevent the
     * current selection from being lost when activating the web editor.
     *
     * @override
     */
    onChangeVariant: function (ev) {
        const componentEl = ev.currentTarget.closest(".js_product");
        componentEl.querySelectorAll("input").forEach(() => {
            this.el.setAttribute("checked", this.el.checked);
        });
        componentEl.querySelectorAll("select option").forEach(() => {
            this.el.setAttribute("selected", this.el.selected);
        });

        this._setUrlHash(componentEl);

        return VariantMixin.onChangeVariant.apply(this, arguments);
    },
    /**
     * @private
     */
    _onClickReviewsLink: function () {
        const collapse = new Collapse(document.querySelector("#o_product_page_reviews_content"));
        collapse.show();
    },
    /**
     * Prevent multiclicks on confirm button when the form is submitted
     *
     * @private
     */
    _onClickConfirmOrder: function () {
        const submitFormButtonEl = this.el.querySelector(
            'form[name="o_wsale_confirm_order"] button[type="submit"]'
        );
        if (submitFormButtonEl) {
            submitFormButtonEl.setAttribute("disabled", true);
            setTimeout(() => submitFormButtonEl.setAttribute("disabled", false), 5000);
        }
    },

    // -------------------------------------
    // Utils
    // -------------------------------------
    /**
     * Update the root product during an Add process.
     *
     * @private
     * @param {Object} formEl
     * @param {Number} productId
     * @param {Number} productTemplateId
     */
    _updateRootProduct(formEl, productId, productTemplateId) {
        this.rootProduct = {
            product_id: productId,
            product_template_id: productTemplateId,
            quantity: parseFloat(formEl.querySelector('input[name="add_qty"]')?.value || 1),
            product_custom_attribute_values: this.getCustomVariantValues(
                formEl.querySelector(".js_product")
            ),
            variant_values: this.getSelectedVariantValues(formEl.querySelector(".js_product")),
            no_variant_attribute_values: this.getNoVariantAttributeValues(
                formEl.querySelector(".js_product")
            ),
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
        const clickedValue = ev.target.value;
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

        const gridEl = this.el.querySelector('#products_grid');
        // Disable transition on all list elements, then switch to the new
        // layout then reenable all transitions after having forced a redraw
        // TODO should probably be improved to allow disabling transitions
        // altogether with a class/option.
        gridEl.querySelectorAll("*").forEach((gridEls) => {
            gridEls.style.transition = "none";
        });
        gridEl.classList.toggle("o_wsale_layout_list", isList);
        void gridEl.offsetWidth;
        gridEl.querySelectorAll("*").forEach((gridEls) => {
            gridEls.style.transition = "";
        });
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
        if (this.el.querySelector(".carousel-indicators")) {
            this.el.addEventListener(
                "slide.bs.carousel.carousel_product_slider",
                this._onSlideCarouselProduct.bind(this)
            );
            window.addEventListener("resize.carousel_product_slider", this.throttleOnResize);
            this._updateJustifyContent();
        }
    },
    /**
     * @override
     */
    destroy() {
        this.el.style.top = "";
        this.el.removeEventListener(
            "slide.bs.carousel.carousel_product_slider",
            this._onSlideCarouselProduct.bind(this)
        );
        window.removeEventListener("resize.carousel_product_slider", this.throttleOnResize);
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
            size += el.style.offsetHeight;
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
        const isLeftIndicators = this.el.classList.contains("o_carousel_product_left_indicators");
        const indicatorsDivEl = isLeftIndicators
            ? this.el.querySelectorAll(".o_carousel_product_indicators")
            : this.el.querySelectorAll(".carousel-indicators");
        let indicatorIndex = Array.from(ev.relatedTarget.parentNode.children).indexOf(ev.relatedTarget)
        indicatorIndex =
            indicatorIndex > -1
                ? indicatorIndex
                : Array.from(this.el.querySelectorAll("li")).indexOf(
                      this.el.querySelector("li.active")
                  );
        const indicatorEl = indicatorsDivEl.querySelector("[data-bs-slide-to=" + indicatorIndex + "]");
        const indicatorsDivSize =
            isLeftIndicators && !isReversed
                ? indicatorsDivEl.offsetHeight
                : indicatorsDivEl.offsetWidth;
        const indicatorSize = isLeftIndicators && !isReversed ? indicatorEl.offsetHeight : indicatorEl.offsetWidth;
        const indicatorPosition = isLeftIndicators && !isReversed ? indicatorEl.top : indicatorEl.left;
        const scrollSize =
            isLeftIndicators && !isReversed
                ? indicatorsDivEl.scrollHeight
                : indicatorsDivEl.scrollWidth;
        let indicatorsPositionDiff = (indicatorPosition + (indicatorSize/2)) - (indicatorsDivSize/2);
        indicatorsPositionDiff = Math.min(indicatorsPositionDiff, scrollSize - indicatorsDivSize);
        this._updateJustifyContent();
        const indicatorsPositionX = isLeftIndicators && !isReversed ? '0' : '-' + indicatorsPositionDiff;
        const indicatorsPositionY = isLeftIndicators && !isReversed ? '-' + indicatorsPositionDiff : '0';
        const translate3D = indicatorsPositionDiff > 0 ? "translate3d(" + indicatorsPositionX + "px," + indicatorsPositionY + "px,0)" : '';
        indicatorsDivEl.style.transform = translate3D;
    },
    /**
     * @private
     */
     _updateJustifyContent: function () {
        const indicatorsDivEl = this.el.querySelector(".carousel-indicators");
        indicatorsDivEl.style.justifyContent = "start";
        if (uiUtils.getSize() <= SIZES.MD) {
            const lastChild = indicatorsDivEl.lastElementChild.getBoundingClientRect();
            const liWidth = this.el.querySelector("li").offsetWidth;
            const indicatorsWidth = indicatorsDivEl.offsetWidth;
            if (lastChild.left + liWidth < indicatorsWidth) {
                indicatorsDivEl.style.justifyContent = "center";
            }
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onMouseWheel: function (ev) {
        ev.preventDefault();
        const carousel = window.Carousel.getOrCreateInstance(this.el);
        if (ev.originalEvent.deltaY > 0) {
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
        if (this.el.querySelector(".o_portal_chatter_composer")) {
            this.el.querySelector(".o_portal_chatter_composer").style.top = "";
        }
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
        const portalChatterComposerEl = this.el.querySelector(".o_portal_chatter_composer");
        if (portalChatterComposerEl) {
            portalChatterComposerEl.style.top = size;
        }
    },
});

export default {
    WebsiteSale: publicWidget.registry.WebsiteSale,
    WebsiteSaleLayout: publicWidget.registry.WebsiteSaleLayout,
    WebsiteSaleProductPage: publicWidget.registry.WebsiteSaleAccordionProduct,
    WebsiteSaleCarouselProduct: publicWidget.registry.websiteSaleCarouselProduct,
    WebsiteSaleProductPageReviews: publicWidget.registry.websiteSaleProductPageReviews,
};
