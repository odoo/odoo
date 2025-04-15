/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.websiteSaleTracking = publicWidget.Widget.extend({
    selector: '.oe_website_sale',
    events: {
        'click form[action="/shop/cart/update"] a.a-submit': '_onAddProductIntoCart',
        'click a[href^="/shop/checkout"]': '_onCheckoutStart',
        'click a[href^="/web/login?redirect"][href*="/shop/checkout"]': '_onCustomerSignin',
        'click form[action="/shop/confirm_order"] a.a-submit': '_onOrder',
        'click form[target="_self"] button[type=submit]': '_onOrderPayment',
        'view_item_event': '_onViewItem',
        'add_to_cart_event': '_onAddToCart',
    },

    /**
     * @override
     */
    start: function () {
        var self = this;

        // ...
        const $confirmation = this.$('div.oe_website_sale_tx_status');
        if ($confirmation.length) {
            const orderID = $confirmation.data('order-id');
            const json = $confirmation.data('order-tracking-info');
            this._vpv('/stats/ecom/order_confirmed/' + orderID);
            self._trackGA('event', 'purchase', json);
        }

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _trackGA: function () {
        const websiteGA = window.gtag || function () {};
        websiteGA.apply(this, arguments);
    },
    /**
     * @private
     */
    _vpv: function (page) { //virtual page view
        this._trackGA('event', 'page_view', {
            'page_path': page,
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onViewItem(event, productTrackingInfo) {
        const trackingInfo = {
            'currency': productTrackingInfo['currency'],
            'value': productTrackingInfo['price'],
            'items': [productTrackingInfo],
        };
        this._trackGA('event', 'view_item', trackingInfo);
    },

    /**
     * @private
     */
    _onAddToCart(event, ...productsTrackingInfo) {
        const trackingInfo = {
            'currency': productsTrackingInfo[0]['currency'],
            'value': productsTrackingInfo.reduce((acc, val) => acc + val['price'] * val['quantity'], 0),
            'items': productsTrackingInfo,
        };
        this._trackGA('event', 'add_to_cart', trackingInfo);
    },

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
        if ($('header#top [href="/web/login"]').length) {
            this._vpv('/stats/ecom/customer_signup');
        }
        this._vpv('/stats/ecom/order_checkout');
    },
    /**
     * @private
     */
    _onOrderPayment: function () {
        var method = $('#payment_method input[name=provider]:checked').nextAll('span:first').text();
        this._vpv('/stats/ecom/order_payment/' + method);
    },
});

export default publicWidget.registry.websiteSaleTracking;
