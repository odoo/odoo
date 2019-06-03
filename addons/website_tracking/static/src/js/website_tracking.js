odoo.define('website_tracking.website_tracking', function (require) {
'use strict';

var concurrency = require('web.concurrency');
var core = require('web.core');
var publicWidget = require('web.public.widget');
var utils = require('web.utils');

var qweb = core.qweb;

publicWidget.registry.productsRecentlyViewedSnippet = publicWidget.Widget.extend({
    selector: '.s_wtracking_products_recently_viewed',
    xmlDependencies: ['/website_tracking/static/src/xml/website_tracking.xml'],
    events: {
        'click .js_add_cart': '_onAddToCart',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._dp = new concurrency.DropPrevious();
    },

    /**
     * @override
     */
    start: function () {
        this._dp.add(this._fetch()).then(this._render.bind(this));
        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _fetch: function () {
        var productDisplayed = parseInt($('input.product_template_id').val());
        var excludedTemplateIds = productDisplayed ? [productDisplayed] : [];
        return this._rpc({
            route: '/shop/products/recently_viewed',
            params: {
                excluded_template_ids: excludedTemplateIds,
            }
        });
    },

    /**
     * @private
     */
    _render: function (res) {
        var products = res['products'];
        if (products.length) {
            var $section = $(qweb.render('website_tracking.productsRecentlyViewed', {
                products: products,
                mobile: window.innerWidth <= 768,
                currency: res['currency'],
                widget: this,
            }));
            this.$('.slider').html($section);
        } else {
            this.$el.hide();
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onAddToCart: function (ev) {
        var self = this;
        var $card = $(ev.currentTarget).closest('.card');
        this._rpc({
            route: "/shop/cart/update_json",
            params: {
                product_id: $card.find('input[data-product-id]').data('product-id'),
                add_qty: 1
            },
        }).then(function (data) {
            var $q = $(".my_cart_quantity");
            if (data.cart_quantity) {
                $q.parents('li:first').removeClass('d-none');
                $q.html(data.cart_quantity).hide().fadeIn(600);
            }

            self._dp.add(self._fetch()).then(self._render.bind(self));

            if ($('.oe_cart')) {
                $(".js_cart_lines").first().before(data['website_sale.cart_lines']).end().remove();
                $(".js_cart_summary").first().before(data['website_sale.short_cart_summary']).end().remove();
            }
        });
    },
});

publicWidget.registry.productsRecentlyViewedUpdate = publicWidget.Widget.extend({
    selector: '#product_details',
    events: {
        'change input.product_id[name="product_id"]': '_onProductChange',
    },
    debounceValue: 3000,

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._onProductChange = _.debounce(this._onProductChange, this.debounceValue);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _updateProductView: function ($target) {
        var productId = parseInt($target.val());
        var productTemplateId = parseInt($('input.product_template_id').val());
        this._rpc({
            route: '/shop/products/recently_viewed_update',
            params: {
                product_template_id: productTemplateId,
                product_id: productId,
            }
        }).then(function (res) {
            if (odoo.__DEBUG__.services['web.session'].is_website_user) {
                if (res.recently_viewed_product_ids) {
                    utils.set_cookie('recently_viewed_product_ids', res.recently_viewed_product_ids);
                }
            }
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onProductChange: function (ev) {
        this._updateProductView($(ev.currentTarget));
    },
});
});
