odoo.define('website_sale.recently_viewed', function (require) {

var publicWidget = require('web.public.widget');
const {getCookie, setCookie} = require('web.utils.cookies');

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
        if (getCookie(cookieName)) {
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
            setCookie(cookieName, productId, 30 * 60, 'optional');
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
