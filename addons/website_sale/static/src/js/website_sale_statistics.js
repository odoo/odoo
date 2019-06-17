odoo.define('website_sale.statistics', function (require) {

var concurrency = require('web.concurrency');
var core = require('web.core');
var publicWidget = require('web.public.widget');
var utils = require('web.utils');
var wSaleUtils = require('website_sale.utils');

var qweb = core.qweb;

publicWidget.registry.productsRecentlyViewedSnippet = publicWidget.Widget.extend({
    selector: '.s_wstatistics_products_recently_viewed',
    xmlDependencies: ['/website_sale/static/src/xml/website_sale_statistics.xml'],
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
        $(window).resize(() => {
            this._addCarousel();
        });
        return this._super.apply(this, arguments);
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
        });
    },

    /**
     * @private
     */
    _render: function (res) {
        this.products = res['products'];
        if (this.products.length) {
            this.webCarousel = $(qweb.render('website_sale.productsRecentlyViewed', {
                products: this.products,
                productFrame: 4,
                currency: res['currency'],
                widget: this,
            }));
            this.mobileCarousel = $(qweb.render('website_sale.productsRecentlyViewed', {
                products: this.products,
                productFrame: 1,
                currency: res['currency'],
                widget: this,
            }));
            this._addCarousel();
        }
    },

    /**
     * @private
     */
    _addCarousel: function () {
        this.$el.find('.slider').html(window.innerWidth <= 768 ? this.mobileCarousel : this.webCarousel);
        // Only way to stop this bs carousel...
        this.$el.find('#o_carousel_recently_viewed_products').carousel('pause');
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

            var $navButton = wSaleUtils.getNavBarButton('.o_wsale_my_cart');
            wSaleUtils.animateClone($navButton, $(ev.currentTarget).parents('.o-product-card'), 25, 40);

            var index = self.$el.find('.carousel-item.active').index();
            self._dp.add(self._fetch()).then(self._render.bind(self)).then(function () {
                self.$el.find('#o_carousel_recently_viewed_products').carousel(index);
            });

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
        this._rpc({
            route: '/shop/products/recently_viewed_update',
            params: {
                product_id: productId,
            }
        }).then(function (res) {
            if (res && odoo.__DEBUG__.services['web.session'].is_website_user) {
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
