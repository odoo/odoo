odoo.define('website_sale.cart', function (require) {
'use strict';

var sAnimations = require('website.content.snippets.animation');
var core = require('web.core');
var _t = core._t;

var timeout;

sAnimations.registry.websiteSaleCartLink = sAnimations.Class.extend({
    selector: '#top_menu a[href$="/shop/cart"]',
    read_events: {
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
    },
    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        if (this.editableMode) {
            return def;
        }

        this.$el.popover({
            trigger: 'manual',
            animation: true,
            html: true,
            title: function () {
                return _t("My Cart");
            },
            container: 'body',
            placement: 'auto',
            template: '<div class="popover mycart-popover" role="tooltip"><div class="arrow"></div><h3 class="popover-header"></h3><div class="popover-body"></div></div>'
        });
        return def;
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
                self.$el.data("bs.popover").config.content = data;
                self.$el.popover("show");
                $('.popover').on('mouseleave', function () {
                    self.$el.trigger('mouseleave');
                });
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
});
});

odoo.define('website_sale.website_sale_category', function (require) {
'use strict';

var sAnimations = require('website.content.snippets.animation');

sAnimations.registry.websiteSaleCategory = sAnimations.Class.extend({
    selector: '#o_shop_collapse_category',
    read_events: {
        'click .fa-chevron-right': '_onOpenClick',
        'click .fa-chevron-down': '_onCloseClick',
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
        $fa.parent().siblings().find('.fa-chevron-down:first').click();
        $fa.parents('li').find('ul:first').show('normal');
        $fa.toggleClass('fa-chevron-down fa-chevron-right');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onCloseClick: function (ev) {
        var $fa = $(ev.currentTarget);
        $fa.parent().find('ul:first').hide('normal');
        $fa.toggleClass('fa-chevron-down fa-chevron-right');
    },
});
});

odoo.define('website_sale.website_sale', function (require) {
'use strict';

var utils = require('web.utils');
var ProductConfiguratorMixin = require('sale.ProductConfiguratorMixin');
var core = require('web.core');
var config = require('web.config');
var sAnimations = require('website.content.snippets.animation');
require("website.content.zoomodoo");

var _t = core._t;

sAnimations.registry.WebsiteSale = sAnimations.Class.extend(ProductConfiguratorMixin, {
    selector: '.oe_website_sale',
    read_events: {
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
        'submit .o_website_sale_search': '_onSubmitSaleSearch',
        'change select[name="country_id"]': '_onChangeCountry',
        'change #shipping_use_same': '_onChangeShippingUseSame',
        'click .toggle_summary': '_onToggleSummary',
        'click input.js_product_change': 'onChangeVariant',
        'change .js_main_product [data-attribute_exclusions]': 'onChangeVariant',
    },

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
    start: function () {
        var def = this._super.apply(this, arguments);
        if (this.editableMode) {
            return def;
        }

        _.each(this.$('div.js_product'), function (product) {
            $('input.js_product_change', product).first().trigger('change');
        });

        // This has to be triggered to compute the "out of stock" feature
        this.triggerVariantChange(this.$el);

        this.$('select[name="country_id"]').change();

        this.$('#checkbox_cgv').trigger('change');

        core.bus.on('resize', this, function () {
            if (config.device.size_class === config.device.SIZES.XL) {
                $('.toggle_summary_div').addClass('d-none d-xl-block');
            }
        });

        this._startZoom();

        return def;
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
        return ProductConfiguratorMixin.getSelectedVariantValues.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

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
            var $q = $(".my_cart_quantity");
            if (data.cart_quantity) {
                $q.parents('li:first').removeClass('d-none');
            }
            else {
                window.location = '/shop/cart';
            }

            $q.html(data.cart_quantity).hide().fadeIn(600);
            $input.val(data.quantity);
            $('.js_quantity[data-line-id='+line_id+']').val(data.quantity).html(data.quantity);

            $(".js_cart_lines").first().before(data['website_sale.cart_lines']).end().remove();
            $(".js_cart_summary").first().before(data['website_sale.short_cart_summary']).end().remove();

            if (data.warning) {
                var cart_alert = $('.oe_cart').parent().find('#data_warning');
                if (cart_alert.length === 0) {
                    $('.oe_cart').prepend('<div class="alert alert-danger alert-dismissable" role="alert" id="data_warning">'+
                            '<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button> ' + data.warning + '</div>');
                }
                else {
                    cart_alert.html('<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button> ' + data.warning);
                }
                $input.val(data.quantity);
            }
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
                mode: 'shipping',
            },
        }).then(function (data) {
            // placeholder phone_code
            //$("input[name='phone']").attr('placeholder', data.phone_code !== 0 ? '+'+ data.phone_code : '');

            // populate states and display
            var selectStates = $("select[name='state_id']");
            // dont reload state at first loading (done in qweb)
            if (selectStates.data('init')===0 || selectStates.find('option').length===1) {
                if (data.states.length) {
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
            return ProductConfiguratorMixin._getProductId.apply(this, arguments);
        }
    },
    /**
     * @private
     */
    _startZoom: function () {
        // Do not activate image zoom for mobile devices, since it might prevent users from scrolling the page
        if (!config.device.isMobile) {
            var autoZoom = $('.ecom-zoomable').data('ecom-zoom-auto') || false,
            factorZoom = parseFloat($('.ecom-zoomable').data('ecom-zoom-factor')) || 1.5,
            attach = '#o-carousel-product';
            _.each($('.ecom-zoomable img[data-zoom]'), function (el) {
                onImageLoaded(el, function () {
                    var $img = $(el);
                    if (!_.str.endsWith(el.src, el.dataset.zoomImage) || // if zoom-img != img
                        el.naturalWidth >= $(attach).width() * factorZoom || el.naturalHeight >= $(attach).height() * factorZoom) {
                        $img.zoomOdoo({event: autoZoom ? 'mouseenter' : 'click', attach: attach});
                        $img.attr('data-zoom', 1); // add cursor (if previously removed)
                    } else {
                        $img.removeAttr('data-zoom'); // remove cursor
                        // remove zooming but keep the attribute because
                        // it can potentially be set back
                        $img.attr('data-zoom-image', '');
                    }
                });
            });
        }

        function onImageLoaded(img, callback) {
            // On Chrome the load event already happened at this point so we
            // have to rely on complete. On Firefox it seems that the event is
            // always triggered after this so we can rely on it.
            //
            // However on the "complete" case we still want to keep listening to
            // the event because if the image is changed later (eg. product
            // configurator) a new load event will be triggered (both browsers).
            $(img).on('load', function () {
                callback();
            });
            if (img.complete) {
                callback();
            }
        }
    },
    /**
     * On website, we display a carousel instead of only one image
     *
     * @override
     * @private
     */
    _updateProductImage: function ($productContainer, productId, productTemplateId, new_carousel, isCombinationPossible) {
        var $img;
        var $carousel = $productContainer.find('#o-carousel-product');

        if (isCombinationPossible === undefined) {
            isCombinationPossible = this.isSelectedVariantAllowed;
        }

        if (new_carousel) {
            // When using the web editor, don't reload this or the images won't
            // be able to be edited depending on if this is done loading before
            // or after the editor is ready.
            if (window.location.search.indexOf('enable_editor') === -1) {
                var $new_carousel = $(new_carousel);
                $carousel.after($new_carousel);
                $carousel.remove();
                $carousel = $new_carousel;
                $carousel.carousel(0);
                this._startZoom();
                // fix issue with carousel height
                this.trigger_up('animation_start_demand', {$target: $carousel});
            }
        }
        else { // compatibility 12.0
            var model = productId ? 'product.product' : 'product.template';
            var modelId = productId || productTemplateId;
            var imageSrc = '/web/image/{0}/{1}/image'
                .replace("{0}", model)
                .replace("{1}", modelId);

            $img = $productContainer.find('img.js_variant_img');
            $img.attr("src", imageSrc);
            $img.parent().attr('data-oe-model', model).attr('data-oe-id', modelId)
                .data('oe-model', model).data('oe-id', modelId);

            var $thumbnail = $productContainer.find('img.js_variant_img_small');
            if ($thumbnail.length !== 0) { // if only one, thumbnails are not displayed
                $thumbnail.attr("src", "/web/image/{0}/{1}/image/90x90"
                    .replace('{0}', model)
                    .replace('{1}', modelId));
                $('.carousel').carousel(0);
            }

            // reset zooming constructs
            $img.filter('[data-zoom-image]').attr('data-zoom-image', $img.attr('src'));
            if ($img.data('zoomOdoo') !== undefined) {
                $img.data('zoomOdoo').isReady = false;
            }
        }

        $carousel.toggleClass('css_not_available', !isCombinationPossible);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickAddCartJSON: function (ev){
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
        if ($aSubmit.hasClass('a-submit-disable')){
            $aSubmit.addClass("disabled");
        }
        if ($aSubmit.hasClass('a-submit-loading')){
            var loading = '<span class="fa fa-cog fa-spin"/>';
            var fa_span = $aSubmit.find('span[class*="fa"]');
            if (fa_span.length){
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
        $(ev.currentTarget).hide();
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
        ProductConfiguratorMixin._toggleDisable.apply(this, arguments);
        $parent.find("#add_to_cart").toggleClass('disabled', !isCombinationPossible);
    },
    /**
     * @private
     */
    _onToggleSummary: function () {
        $('.toggle_summary_div').toggleClass('d-none');
        $('.toggle_summary_div').removeClass('d-xl-block');
    },
});


sAnimations.registry.websiteSaleCart = sAnimations.Class.extend({
    selector: '.oe_website_sale .oe_cart',
    read_events: {
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
        var $old = $('.all_shipping').find('.card.border_primary');
        $old.find('.btn-ship').toggle();
        $old.addClass('js_change_shipping');
        $old.removeClass('border_primary');

        var $new = $(ev.currentTarget).parent('div.one_kanban').find('.card');
        $new.find('.btn-ship').toggle();
        $new.removeClass('js_change_shipping');
        $new.addClass('border_primary');

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
});
