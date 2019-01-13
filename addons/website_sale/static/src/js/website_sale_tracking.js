odoo.define('website_sale.tracking', function (require) {

var sAnimations = require('website.content.snippets.animation');

sAnimations.registry.websiteSaleTracking = sAnimations.Class.extend({
    selector: '.oe_website_sale',
    read_events: {
        'click form[action="/shop/cart/update"] a.a-submit': '_onAddProductIntoCart',
        'click a[href="/shop/checkout"]': '_onCheckoutStart',
        'click div.oe_cart a[href^="/web?redirect"][href$="/shop/checkout"]': '_onCustomerSignin',
        'click form[action="/shop/confirm_order"] a.a-submit': '_onOrder',
        'click form[target="_self"] button[type=submit]': '_onOrderPayment',
    },

    /**
     * @override
     */
    start: function () {
        var self = this;
        var def = this._super.apply(this, arguments);
        if (this.editableMode) {
            return def;
        }

        // Watching a product
        if (this.$el.is('#product_detail')) {
            var productID = this.$('input[name="product_id"]').attr('value');
            this._vpv('/stats/ecom/product_view/' + productID);
        }

        // ...
        if (this.$('div.oe_website_sale_tx_status').length) {
            this._trackGA('require', 'ecommerce');

            var orderID = this.$('div.oe_website_sale_tx_status').data('order-id');
            this._vpv('/stats/ecom/order_confirmed/' + orderID);

            this._rpc({
                route: '/shop/tracking_last_order/',
            }).then(function (o) {
                self._trackGA('ecommerce:clear');

                if (o.transaction && o.lines) {
                    self._trackGA('ecommerce:addTransaction', o.transaction);
                    _.forEach(o.lines, function (line) {
                        self._trackGA('ecommerce:addItem', line);
                    });
                }
                self._trackGA('ecommerce:send');
            });
        }

        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _trackGA: function () {
        websiteGA = window.ga || function () {};
        websiteGA.apply(this, arguments);
    },
    /**
     * @private
     */
    _vpv: function (page) { //virtual page view
        this._trackGA('send', 'pageview', {
          'page': page,
          'title': document.title,
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onAddProductIntoCart: function () {
        var productID = this.$('input[name="product_id"]').attr('value');
        this._vpv('/stats/ecom/product_add_to_cart/' + productID);
    },
    /**
     * @private
     */
    _onCheckoutStart: function () {
        this._vpv('/stats/ecom/customer_checkout');
    },
    /**
     * @private
     */
    _onCustomerSignin: function () {
        this._vpv('/stats/ecom/customer_signin');
    },
    /**
     * @private
     */
    _onOrder: function () {
        if ($('#top_menu [href="/web/login"]').length) {
            this._vpv('/stats/ecom/customer_signup');
        }
        this._vpv('/stats/ecom/order_checkout');
    },
    /**
     * @private
     */
    _onOrderPayment: function () {
        var method = $('#payment_method input[name=acquirer]:checked').nextAll('span:first').text();
        this._vpv('/stats/ecom/order_payment/' + method);
    },
});

});
