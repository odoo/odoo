odoo.define('website_sale.recently_viewed', function (require) {

var concurrency = require('web.concurrency');
var config = require('web.config');
var core = require('web.core');
var publicWidget = require('web.public.widget');
var utils = require('web.utils');
var wSaleUtils = require('website_sale.utils');

var qweb = core.qweb;

publicWidget.registry.productsRecentlyViewedSnippet = publicWidget.Widget.extend({
    selector: '.s_wsale_products_recently_viewed',
    xmlDependencies: ['/website_sale/static/src/xml/website_sale_recently_viewed.xml'],
    disabledInEditableMode: false,
    read_events: {
        'click .js_add_cart': '_onAddToCart',
        'click .js_remove': '_onRemove',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);
        this._dp = new concurrency.DropPrevious();
        this.uniqueId = _.uniqueId('o_carousel_recently_viewed_products_');
        this._onResizeChange = _.debounce(this._addCarousel, 100);
    },
    /**
     * @override
     */
    start: function () {
        this._dp.add(this._fetch()).then(this._render.bind(this));
        $(window).resize(() => {
            this._onResizeChange();
        });
        return this._super.apply(this, arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this._super(...arguments);
        this.$el.addClass('d-none');
        this.$el.find('.slider').html('');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _fetch: function () {
        return this._rpc({
            route: '/shop/products/recently_viewed',
        }).then(res => {
            var products = res['products'];

            // In edit mode, if the current visitor has no recently viewed
            // products, use demo data.
            if (this.editableMode && (!products || !products.length)) {
                return {
                    'products': [{
                        id: 0,
                        website_url: '#',
                        display_name: 'Product 1',
                        price: '$ <span class="oe_currency_value">750.00</span>',
                    }, {
                        id: 0,
                        website_url: '#',
                        display_name: 'Product 2',
                        price: '$ <span class="oe_currency_value">750.00</span>',
                    }, {
                        id: 0,
                        website_url: '#',
                        display_name: 'Product 3',
                        price: '$ <span class="oe_currency_value">750.00</span>',
                    }, {
                        id: 0,
                        website_url: '#',
                        display_name: 'Product 4',
                        price: '$ <span class="oe_currency_value">750.00</span>',
                    }],
                };
            }

            return res;
        });
    },
    /**
     * @private
     */
    _render: function (res) {
        var products = res['products'];
        var mobileProducts = [], webProducts = [], productsTemp = [];
        _.each(products, function (product) {
            if (productsTemp.length === 4) {
                webProducts.push(productsTemp);
                productsTemp = [];
            }
            productsTemp.push(product);
            mobileProducts.push([product]);
        });
        if (productsTemp.length) {
            webProducts.push(productsTemp);
        }

        this.mobileCarousel = $(qweb.render('website_sale.productsRecentlyViewed', {
            uniqueId: this.uniqueId,
            productFrame: 1,
            productsGroups: mobileProducts,
        }));
        this.webCarousel = $(qweb.render('website_sale.productsRecentlyViewed', {
            uniqueId: this.uniqueId,
            productFrame: 4,
            productsGroups: webProducts,
        }));
        this._addCarousel();
        this.$el.toggleClass('d-none', !(products && products.length));
    },
    /**
     * Add the right carousel depending on screen size.
     * @private
     */
    _addCarousel: function () {
        var carousel = config.device.size_class <= config.device.SIZES.SM ? this.mobileCarousel : this.webCarousel;
        this.$('.slider').html(carousel).css('display', ''); // Removing display is kept for compatibility (it was hidden before)
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Add product to cart and reload the carousel.
     * @private
     * @param {Event} ev
     */
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
            wSaleUtils.updateCartNavBar(data);
            var $navButton = $('header .o_wsale_my_cart').first();
            var fetch = self._fetch();
            var animation = wSaleUtils.animateClone($navButton, $(ev.currentTarget).parents('.o_carousel_product_card'), 25, 40);
            Promise.all([fetch, animation]).then(function (values) {
                self._render(values[0]);
            });
        });
    },

    /**
     * Remove product from recently viewed products.
     * @private
     * @param {Event} ev
     */
    _onRemove: function (ev) {
        var self = this;
        var $card = $(ev.currentTarget).closest('.card');
        this._rpc({
            route: "/shop/products/recently_viewed_delete",
            params: {
                product_id: $card.find('input[data-product-id]').data('product-id'),
            },
        }).then(function (data) {
            self._render(data);
        });
    },
});

publicWidget.registry.productsRecentlyViewedUpdate = publicWidget.Widget.extend({
    selector: '#product_detail',
    events: {
        'change input.product_id[name="product_id"]': '_onProductChange',
    },
    debounceValue: 8000,

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

    /**
     * Debounced method that wait some time before marking the product as viewed.
     * @private
     * @param {HTMLInputElement} $input
     */
    _updateProductView: function ($input) {
        var productId = parseInt($input.val());
        var cookieName = 'seen_product_id_' + productId;
        if (! parseInt(this.el.dataset.viewTrack, 10)) {
            return; // Is not tracked
        }
        if (utils.get_cookie(cookieName)) {
            return; // Already tracked in the last 30min
        }
        if ($(this.el).find('.js_product.css_not_available').length) {
            return; // Variant not possible
        }
        this._rpc({
            route: '/shop/products/recently_viewed_update',
            params: {
                product_id: productId,
            }
        }).then(function (res) {
            if (res && res.visitor_uuid) {
                utils.set_cookie('visitor_uuid', res.visitor_uuid);
            }
            utils.set_cookie(cookieName, productId, 30 * 60);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Call debounced method when product change to reset timer.
     * @private
     * @param {Event} ev
     */
    _onProductChange: function (ev) {
        this._updateProductView($(ev.currentTarget));
    },
});
});
