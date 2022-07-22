odoo.define('website_sale.cart', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var core = require('web.core');
var _t = core._t;

var timeout;

publicWidget.registry.websiteSaleCartLink = publicWidget.Widget.extend({
    selector: '#top_menu a[href$="/shop/cart"]',
    events: {
        'mouseenter': '_onMouseEnter',
        'mouseleave': '_onMouseLeave',
        'click': '_onClick',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._popoverRPC = null;
        this._onVisibilityChange = this._onVisibilityChange.bind(this);
    },
    /**
     * @override
     */
    willStart() {
        return Promise.all([this._super.apply(this, arguments), this._updateCartQuantityValue()]);
    },
    /**
     * @override
     */
    start: function () {
        this.$el.popover({
            trigger: 'manual',
            animation: true,
            html: true,
            title: function () {
                return _t("My Cart");
            },
            container: 'body',
            placement: 'auto',
            template: '<div class="popover mycart-popover" role="tooltip"><div class="tooltip-arrow"></div><h3 class="popover-header"></h3><div class="popover-body"></div></div>'
        });
        window.addEventListener('visibilitychange', this._onVisibilityChange);
        this._updateCartQuantityText();
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy() {
        window.removeEventListener('visibilitychange', this._onVisibilityChange);
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onMouseEnter: function (ev) {
        var self = this;
        clearTimeout(timeout);
        $(this.selector).not(ev.currentTarget).popover('hide');
        timeout = setTimeout(function () {
            if (!self.$el.is(':hover') || $('.mycart-popover:visible').length) {
                return;
            }
            self._popoverRPC = $.get("/shop/cart", {
                type: 'popover',
            }).then(function (data) {
                const popover = Popover.getInstance(self.$el[0]);
                popover._config.content = data;
                popover.setContent(popover.getTipElement());
                self.$el.popover("show");
                $('.popover').on('mouseleave', function () {
                    self.$el.trigger('mouseleave');
                });
                self.cartQty = +$(data).find('.o_wsale_cart_quantity').text();
                sessionStorage.setItem('website_sale_cart_quantity', self.cartQty);
                self._updateCartQuantityText();
            });
        }, 300);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onMouseLeave: function (ev) {
        var self = this;
        setTimeout(function () {
            if ($('.popover:hover').length) {
                return;
            }
            if (!self.$el.is(':hover')) {
               self.$el.popover('hide');
            }
        }, 1000);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClick: function (ev) {
        // When clicking on the cart link, prevent any popover to show up (by
        // clearing the related setTimeout) and, if a popover rpc is ongoing,
        // wait for it to be completed before going to the link's href. Indeed,
        // going to that page may perform the same computation the popover rpc
        // is already doing.
        clearTimeout(timeout);
        if (this._popoverRPC && this._popoverRPC.state() === 'pending') {
            ev.preventDefault();
            var href = ev.currentTarget.href;
            this._popoverRPC.then(function () {
                window.location.href = href;
            });
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onVisibilityChange(ev) {
        if (ev.target.visibilityState === 'visible'){
            this._updateCartQuantityValue().then(this._updateCartQuantityText.bind(this));
        }
    },
    /**
     * @private
     */
    async _updateCartQuantityValue() {
        if ('website_sale_cart_quantity' in sessionStorage) {
            this.cartQty = sessionStorage.getItem('website_sale_cart_quantity');
        }
        if (this.el.querySelector('.my_cart_quantity').innerText != this.cartQty) {
            return this._rpc({route: "/shop/cart/quantity"}).then((cartQty) => {
                this.cartQty = cartQty;
                sessionStorage.setItem('website_sale_cart_quantity', this.cartQty);
            });
        }
    },
    /**
     * @private
     */
    _updateCartQuantityText() {
        if (this.cartQty !== undefined) {
            this.el.querySelector('.my_cart_quantity').innerText = this.cartQty;
        }
    }
});
});

odoo.define('website_sale.website_sale_category', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.websiteSaleCategory = publicWidget.Widget.extend({
    selector: '#o_shop_collapse_category',
    events: {
        'click .fa-angle-right': '_onOpenClick',
        'click .fa-angle-down': '_onCloseClick',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onOpenClick: function (ev) {
        var $fa = $(ev.currentTarget);
        $fa.parent().siblings().find('.fa-angle-down:first').click();
        $fa.parents('li').find('ul:first').show('normal');
        $fa.toggleClass('fa-angle-down fa-angle-right');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onCloseClick: function (ev) {
        var $fa = $(ev.currentTarget);
        $fa.parent().find('ul:first').hide('normal');
        $fa.toggleClass('fa-angle-down fa-angle-right');
    },
});
});

odoo.define('website_sale.website_sale', function (require) {
'use strict';

var core = require('web.core');
var config = require('web.config');
var publicWidget = require('web.public.widget');
var VariantMixin = require('website_sale.VariantMixin');
var wSaleUtils = require('website_sale.utils');
const cartHandlerMixin = wSaleUtils.cartHandlerMixin;
require("web.zoomodoo");
const {extraMenuUpdateCallbacks} = require('website.content.menu');
const dom = require('web.dom');
const { cartesian } = require('@web/core/utils/arrays');
const { ComponentWrapper } = require('web.OwlCompatibility');
const { ProductImageViewerWrapper } = require("@website_sale/js/components/website_sale_image_viewer");

publicWidget.registry.WebsiteSale = publicWidget.Widget.extend(VariantMixin, cartHandlerMixin, {
    selector: '.oe_website_sale',
    events: _.extend({}, VariantMixin.events || {}, {
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
        'click .show_coupon': '_onClickShowCoupon',
        'submit .o_wsale_products_searchbar_form': '_onSubmitSaleSearch',
        'change select[name="country_id"]': '_onChangeCountry',
        'change #shipping_use_same': '_onChangeShippingUseSame',
        'click .toggle_summary': '_onToggleSummary',
        'click #add_to_cart, .o_we_buy_now, #products_grid .o_wsale_product_btn .a-submit': 'async _onClickAdd',
        'click input.js_product_change': 'onChangeVariant',
        'change .js_main_product [data-attribute_exclusions]': 'onChangeVariant',
        'change oe_advanced_configurator_modal [data-attribute_exclusions]': 'onChangeVariant',
        'click .o_product_page_reviews_link': '_onClickReviewsLink',
    }),

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this._changeCartQuantity = _.debounce(this._changeCartQuantity.bind(this), 500);
        this._changeCountry = _.debounce(this._changeCountry.bind(this), 500);

        this.isWebsite = true;

        delete this.events['change .main_product:not(.in_cart) input.js_quantity'];
        delete this.events['change [data-attribute_exclusions]'];
    },
    /**
     * @override
     */
    start() {
        const def = this._super(...arguments);

        this._applyHashFromSearch();

        _.each(this.$('div.js_product'), function (product) {
            $('input.js_product_change', product).first().trigger('change');
        });

        // This has to be triggered to compute the "out of stock" feature and the hash variant changes
        this.triggerVariantChange(this.$el);

        this.$('select[name="country_id"]').change();

        core.bus.on('resize', this, function () {
            if (config.device.size_class === config.device.SIZES.XL) {
                $('.toggle_summary_div').addClass('d-none d-xl-block');
            }
        });

        this._startZoom();

        window.addEventListener('hashchange', () => {
            this._applyHash();
            this.triggerVariantChange(this.$el);
        });

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
    getSelectedVariantValues: function ($container) {
        var combination = $container.find('input.js_product_change:checked')
            .data('combination');

        if (combination) {
            return combination;
        }
        return VariantMixin.getSelectedVariantValues.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _applyHash: function () {
        var hash = window.location.hash.substring(1);
        if (hash) {
            var params = $.deparam(hash);
            if (params['attr']) {
                var attributeIds = params['attr'].split(',');
                var $inputs = this.$('input.js_variant_change, select.js_variant_change option');
                _.each(attributeIds, function (id) {
                    var $toSelect = $inputs.filter('[data-value_id="' + id + '"]');
                    if ($toSelect.is('input[type="radio"]')) {
                        $toSelect.prop('checked', true);
                    } else if ($toSelect.is('option')) {
                        $toSelect.prop('selected', true);
                    }
                });
                this._changeAttribute(['.css_attribute_color', '.o_variant_pills']);
            }
        }
    },

    /**
     * Sets the url hash from the selected product options.
     *
     * @private
     */
    _setUrlHash: function ($parent) {
        var $attributes = $parent.find('input.js_variant_change:checked, select.js_variant_change option:selected');
        var attributeIds = _.map($attributes, function (elem) {
            return $(elem).data('value_id');
        });
        window.location.hash = 'attr=' + attributeIds.join(',');
    },
    /**
     * Set the checked values active.
     *
     * @private
     * @param {Array} valueSelectors Selectors
     */
    _changeAttribute: function (valueSelectors) {
        _.each(valueSelectors, function (selector) {
            $(selector).removeClass("active")
                       .filter(':has(input:checked)')
                       .addClass("active");
        });
    },
    /**
     * @private
     */
    _changeCartQuantity: function ($input, value, $dom_optional, line_id, productIDs) {
        _.each($dom_optional, function (elem) {
            $(elem).find('.js_quantity').text(value);
            productIDs.push($(elem).find('span[data-product-id]').data('product-id'));
        });
        $input.data('update_change', true);

        this._rpc({
            route: "/shop/cart/update_json",
            params: {
                line_id: line_id,
                product_id: parseInt($input.data('product-id'), 10),
                set_qty: value
            },
        }).then(function (data) {
            $input.data('update_change', false);
            var check_value = parseInt($input.val() || 0, 10);
            if (isNaN(check_value)) {
                check_value = 1;
            }
            if (value !== check_value) {
                $input.trigger('change');
                return;
            }
            sessionStorage.setItem('website_sale_cart_quantity', data.cart_quantity);
            if (!data.cart_quantity) {
                return window.location = '/shop/cart';
            }
            $input.val(data.quantity);
            $('.js_quantity[data-line-id='+line_id+']').val(data.quantity).text(data.quantity);

            wSaleUtils.updateCartNavBar(data);
            wSaleUtils.showWarning(data.warning);
        });
    },
    /**
     * @private
     */
    _changeCountry: function () {
        if (!$("#country_id").val()) {
            return;
        }
        this._rpc({
            route: "/shop/country_infos/" + $("#country_id").val(),
            params: {
                mode: $("#country_id").attr('mode'),
            },
        }).then(function (data) {
            // placeholder phone_code
            $("input[name='phone']").attr('placeholder', data.phone_code !== 0 ? '+'+ data.phone_code : '');

            // populate states and display
            var selectStates = $("select[name='state_id']");
            // dont reload state at first loading (done in qweb)
            if (selectStates.data('init')===0 || selectStates.find('option').length===1) {
                if (data.states.length || data.state_required) {
                    selectStates.html('');
                    _.each(data.states, function (x) {
                        var opt = $('<option>').text(x[1])
                            .attr('value', x[0])
                            .attr('data-code', x[2]);
                        selectStates.append(opt);
                    });
                    selectStates.parent('div').show();
                } else {
                    selectStates.val('').parent('div').hide();
                }
                selectStates.data('init', 0);
            } else {
                selectStates.data('init', 0);
            }

            // manage fields order / visibility
            if (data.fields) {
                if ($.inArray('zip', data.fields) > $.inArray('city', data.fields)){
                    $(".div_zip").before($(".div_city"));
                } else {
                    $(".div_zip").after($(".div_city"));
                }
                var all_fields = ["street", "zip", "city", "country_name"]; // "state_code"];
                _.each(all_fields, function (field) {
                    $(".checkout_autoformat .div_" + field.split('_')[0]).toggle($.inArray(field, data.fields)>=0);
                });
            }

            if ($("label[for='zip']").length) {
                $("label[for='zip']").toggleClass('label-optional', !data.zip_required);
                $("label[for='zip']").get(0).toggleAttribute('required', !!data.zip_required);
            }
            if ($("label[for='zip']").length) {
                $("label[for='state_id']").toggleClass('label-optional', !data.state_required);
                $("label[for='state_id']").get(0).toggleAttribute('required', !!data.state_required);
            }
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
        // Do not activate image zoom on hover for mobile devices
        const salePage = document.querySelector(".o_wsale_product_page");
        if (!salePage || config.device.mobile || this._getProductImageWidth() === "none") {
            return;
        }
        this._cleanupZoom();
        this.zoomCleanup = [];
        // Zoom on hover
        if (salePage.dataset.ecomZoomAuto) {
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
                    const dialog = new ComponentWrapper(this, ProductImageViewerWrapper, {
                        selectedImageIdx: [...images].indexOf(image),
                        images,
                    });
                    dialog.mount(document.body);
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
    _onClickAdd: function (ev) {
        ev.preventDefault();
        var def = () => {
            this.getCartHandlerOptions(ev);
            return this._handleAdd($(ev.currentTarget).closest('form'));
        };
        if ($('.js_add_cart_variants').children().length) {
            return this._getCombinationInfo(ev).then(() => {
                return !$(ev.target).closest('.js_product').hasClass("css_not_available") ? def() : Promise.resolve();
            });
        }
        return def();
    },
    /**
     * Initializes the optional products modal
     * and add handlers to the modal events (confirm, back, ...)
     *
     * @private
     * @param {$.Element} $form the related webshop form
     */
    _handleAdd: function ($form) {
        var self = this;
        this.$form = $form;

        var productSelector = [
            'input[type="hidden"][name="product_id"]',
            'input[type="radio"][name="product_id"]:checked'
        ];

        var productReady = this.selectOrCreateProduct(
            $form,
            parseInt($form.find(productSelector.join(', ')).first().val(), 10),
            $form.find('.product_template_id').val(),
            false
        );

        return productReady.then(function (productId) {
            $form.find(productSelector.join(', ')).val(productId);
            self._updateRootProduct($form, productId);
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

        const $product = $('#product_detail');
        const productTrackingInfo = $product.data('product-tracking-info');
        if (productTrackingInfo) {
            productTrackingInfo.quantity = params.quantity;
            $product.trigger('add_to_cart_event', [productTrackingInfo]);
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
        $(ev.currentTarget).parents('.thumbnail').toggleClass('disabled');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onChangeCartQuantity: function (ev) {
        var $input = $(ev.currentTarget);
        if ($input.data('update_change')) {
            return;
        }
        var value = parseInt($input.val() || 0, 10);
        if (isNaN(value)) {
            value = 1;
        }
        var $dom = $input.closest('tr');
        // var default_price = parseFloat($dom.find('.text-danger > span.oe_currency_value').text());
        var $dom_optional = $dom.nextUntil(':not(.optional_product.info)');
        var line_id = parseInt($input.data('line-id'), 10);
        var productIDs = [parseInt($input.data('product-id'), 10)];
        this._changeCartQuantity($input, value, $dom_optional, line_id, productIDs);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickSuggestedProduct: function (ev) {
        $(ev.currentTarget).prev('input').val(1).trigger('change');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickSubmit: function (ev, forceSubmit) {
        if ($(ev.currentTarget).is('#add_to_cart, #products_grid .a-submit') && !forceSubmit) {
            return;
        }
        var $aSubmit = $(ev.currentTarget);
        if (!ev.isDefaultPrevented() && !$aSubmit.is(".disabled")) {
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
        if (!ev.isDefaultPrevented()) {
            ev.preventDefault();
            $(ev.currentTarget).closest("form").submit();
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onMouseupAddCartLabel: function (ev) { // change price when they are variants
        var $label = $(ev.currentTarget);
        var $price = $label.parents("form:first").find(".oe_price .oe_currency_value");
        if (!$price.data("price")) {
            $price.data("price", parseFloat($price.text()));
        }
        var value = $price.data("price") + parseFloat($label.find(".badge span").text() || 0);

        var dec = value % 1;
        $price.html(value + (dec < 0.01 ? ".00" : (dec < 1 ? "0" : "") ));
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickShowCoupon: function (ev) {
        $(".show_coupon").hide();
        $('.coupon_form').removeClass('d-none');
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
        if (!ev.isDefaultPrevented() && !$this.is(".disabled")) {
            ev.preventDefault();
            var oldurl = $this.attr('action');
            oldurl += (oldurl.indexOf("?")===-1) ? "?" : "";
            var search = $this.find('input.search-query');
            window.location = oldurl + '&' + search.attr('name') + '=' + encodeURIComponent(search.val());
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onChangeCountry: function (ev) {
        if (!this.$('.checkout_autoformat').length) {
            return;
        }
        this._changeCountry();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onChangeShippingUseSame: function (ev) {
        $('.ship_to_other').toggle(!$(ev.currentTarget).prop('checked'));
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
    _onToggleSummary: function () {
        $('.toggle_summary_div').toggleClass('d-none');
        $('.toggle_summary_div').removeClass('d-xl-block');
    },
    /**
     * @private
     */
    _isValidCombination(combination, attributeExclusions) {
        if (attributeExclusions.exclusions) {
            for (const attribute of combination) {
                if (!attributeExclusions.exclusions.hasOwnProperty(attribute)) {
                    continue;
                }
                for (const excludedAttribute of attributeExclusions.exclusions[attribute]) {
                    if (combination.includes(excludedAttribute)) {
                        return false;
                    }
                }
            }
        }
        if (attributeExclusions.archived_combination) {
            for (const archivedCombination of attributeExclusions.archived_combination) {
                if (archivedCombination.length !== combination.length) {
                    continue;
                }
                if (archivedCombination.filter((attr) => combination.includes(attr)).length === combination.length) {
                    return false;
                }
            }
        }
        return true;
    },
    /**
     * @private
     */
    _applyHashFromSearch() {
        const params = $.deparam(window.location.search.slice(1));
        if (params.attrib) {
            const attributeValuesPerAttribute = {};
            for (const attrib of params.attrib) {
                const [ptalId, ptavId] = attrib.split('-');
                const attribValueSelector = `.js_variant_change[name="ptal-${ptalId}"][value="${ptavId}"]`;
                const attribValue = this.el.querySelector(attribValueSelector);
                if (attribValue !== null) {
                    if (!attributeValuesPerAttribute[ptalId]) {
                        attributeValuesPerAttribute[ptalId] = [];
                    }
                    attributeValuesPerAttribute[ptalId].push(ptavId);
                }
            }
            const attributeSelection = this.el.querySelector('.js_add_cart_variants');
            const attributeExclusions = attributeSelection && JSON.parse(attributeSelection.dataset.attribute_exclusions);
            if (attributeExclusions && Object.values(attributeValuesPerAttribute).length > 1) {
                const allCombinations = cartesian(...Object.values(attributeValuesPerAttribute));
                const selectedCombination = allCombinations.find(c => this._isValidCombination(c, attributeExclusions));

                if (selectedCombination && selectedCombination.length) {
                    window.location.hash = `attr=${selectedCombination.join(',')}`;
                }
            }
        }
        this._applyHash();
    },
    /**
     * @private
     */
    _onClickReviewsLink: function () {
        $('#o_product_page_reviews_content').collapse('show');
    },

    // -------------------------------------
    // Utils
    // -------------------------------------
    /**
     * Update the root product during an Add process.
     *
     * @private
     * @param {Object} $form
     * @param {Number} productId
     */
    _updateRootProduct($form, productId) {
        this.rootProduct = {
            product_id: productId,
            quantity: parseFloat($form.find('input[name="add_qty"]').val() || 1),
            product_custom_attribute_values: this.getCustomVariantValues($form.find('.js_product')),
            variant_values: this.getSelectedVariantValues($form.find('.js_product')),
            no_variant_attribute_values: this.getNoVariantAttributeValues($form.find('.js_product'))
        };
    },
});

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
            this._rpc({
                route: '/shop/save_shop_layout_mode',
                params: {
                    'layout_mode': isList ? 'list' : 'grid',
                },
            });
        }
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

publicWidget.registry.websiteSaleCart = publicWidget.Widget.extend({
    selector: '.oe_website_sale .oe_cart',
    events: {
        'click .js_change_shipping': '_onClickChangeShipping',
        'click .js_edit_address': '_onClickEditAddress',
        'click .js_delete_product': '_onClickDeleteProduct',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClickChangeShipping: function (ev) {
        var $old = $('.all_shipping').find('.card.border.border-primary');
        $old.find('.btn-ship').toggle();
        $old.addClass('js_change_shipping');
        $old.removeClass('border border-primary');

        var $new = $(ev.currentTarget).parent('div.one_kanban').find('.card');
        $new.find('.btn-ship').toggle();
        $new.removeClass('js_change_shipping');
        $new.addClass('border border-primary');

        var $form = $(ev.currentTarget).parent('div.one_kanban').find('form.d-none');
        $.post($form.attr('action'), $form.serialize()+'&xhr=1');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickEditAddress: function (ev) {
        ev.preventDefault();
        $(ev.currentTarget).closest('div.one_kanban').find('form.d-none').attr('action', '/shop/address').submit();
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickDeleteProduct: function (ev) {
        ev.preventDefault();
        $(ev.currentTarget).closest('tr').find('.js_quantity').val(0).trigger('change');
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
        extraMenuUpdateCallbacks.push(this._updateCarouselPosition.bind(this));
        if (this.$target.find('.carousel-indicators').length > 0) {
            this.$target.on('slide.bs.carousel.carousel_product_slider', this._onSlideCarouselProduct.bind(this));
            $(window).on('resize.carousel_product_slider', _.throttle(this._onSlideCarouselProduct.bind(this), 150));
            this._updateJustifyContent();
        }
    },
    /**
     * @override
     */
    destroy() {
        this.$target.css('top', '');
        this.$target.off('.carousel_product_slider');
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _updateCarouselPosition() {
        this.$target.css('top', dom.scrollFixedOffset() + 5);
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
        const isReversed = this.$target.css('flex-direction') === "column-reverse";
        const isLeftIndicators = this.$target.hasClass('o_carousel_product_left_indicators');
        const $indicatorsDiv = isLeftIndicators ? this.$target.find('.o_carousel_product_indicators') : this.$target.find('.carousel-indicators');
        let indicatorIndex = $(ev.relatedTarget).index();
        indicatorIndex = indicatorIndex > -1 ? indicatorIndex : this.$target.find('li.active').index();
        const $indicator = $indicatorsDiv.find('[data-bs-slide-to=' + indicatorIndex + ']');
        const indicatorsDivSize = isLeftIndicators && !isReversed ? $indicatorsDiv.outerHeight() : $indicatorsDiv.outerWidth();
        const indicatorSize = isLeftIndicators && !isReversed ? $indicator.outerHeight() : $indicator.outerWidth();
        const indicatorPosition = isLeftIndicators && !isReversed ? $indicator.position().top : $indicator.position().left;
        const scrollSize = isLeftIndicators && !isReversed ? $indicatorsDiv[0].scrollHeight : $indicatorsDiv[0].scrollWidth;
        let indicatorsPositionDiff = (indicatorPosition + (indicatorSize/2)) - (indicatorsDivSize/2);
        indicatorsPositionDiff = Math.min(indicatorsPositionDiff, scrollSize - indicatorsDivSize);
        this._updateJustifyContent();
        const indicatorsPositionX = isLeftIndicators && !isReversed ? '0' : '-' + indicatorsPositionDiff;
        const indicatorsPositionY = isLeftIndicators && !isReversed ? '-' + indicatorsPositionDiff : '0';
        const translate3D = indicatorsPositionDiff > 0 ? "translate3d(" + indicatorsPositionX + "px," + indicatorsPositionY + "px,0)" : '';
        $indicatorsDiv.css("transform", translate3D);
    },
    /**
     * @private
     */
     _updateJustifyContent: function () {
        const $indicatorsDiv = this.$target.find('.carousel-indicators');
        $indicatorsDiv.css('justify-content', 'start');
        if (config.device.size_class <= config.device.SIZES.MD) {
            if (($indicatorsDiv.children().last().position().left + this.$target.find('li').outerWidth()) < $indicatorsDiv.outerWidth()) {
                $indicatorsDiv.css('justify-content', 'center');
            }
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onMouseWheel: function (ev) {
        ev.preventDefault();
        if (ev.originalEvent.deltaY > 0) {
            this.$target.carousel('next');
        } else {
            this.$target.carousel('prev');
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
        this.$target.find('.o_portal_chatter_composer').css('top', '');
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _updateChatterComposerPosition() {
        this.$target.find('.o_portal_chatter_composer').css('top', dom.scrollFixedOffset() + 20);
    },
});

return {
    WebsiteSale: publicWidget.registry.WebsiteSale,
    WebsiteSaleLayout: publicWidget.registry.WebsiteSaleLayout,
    websiteSaleCart: publicWidget.registry.websiteSaleCart,
    WebsiteSaleCarouselProduct: publicWidget.registry.websiteSaleCarouselProduct,
    WebsiteSaleProductPageReviews: publicWidget.registry.websiteSaleProductPageReviews,
};

});

odoo.define('website_sale.price_range_option', function (require) {
'use strict';

const publicWidget = require('web.public.widget');

publicWidget.registry.multirangePriceSelector = publicWidget.Widget.extend({
    selector: '#o_wsale_price_range_option',
    events: {
        'newRangeValue input[type="range"]': '_onPriceRangeSelected',
    },

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onPriceRangeSelected(ev) {
        const range = ev.currentTarget;
        const search = $.deparam(window.location.search.substring(1));
        delete search.min_price;
        delete search.max_price;
        if (parseFloat(range.min) !== range.valueLow) {
            search['min_price'] = range.valueLow;
        }
        if (parseFloat(range.max) !== range.valueHigh) {
            search['max_price'] = range.valueHigh;
        }
        window.location.search = $.param(search);
    },
});
});
