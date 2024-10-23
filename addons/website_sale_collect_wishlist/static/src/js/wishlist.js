/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import '@website_sale_wishlist/js/website_sale_wishlist';
import { rpc } from "@web/core/network/rpc";


publicWidget.registry.ProductWishlist.include({
    
    events: Object.assign({}, publicWidget.registry.ProductWishlist.prototype.events, {
        'click .o_update_wishlist': '_onClickUpdateWishlist',
    }),

    // #=== EVENT HANDLERS ===#
    _onClickUpdateWishlist: async function (ev) {
        this._addNewProducts($(ev.currentTarget));
        this._onClickRemoveWishlist(ev);
        window.location.reload();
    },

    /**
     * Remove a product from the cart.
     *
     * @private
     * @param {Event} ev
     */
    async _onClickRemoveWishlist(ev) {
        await rpc('/shop/cart/update_json', {
            product_id: parseInt(ev.target.dataset.productId, 10),
            set_qty: 0,
            display: false,
        });
    },
});
