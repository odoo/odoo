/** @odoo-module **/

import publicWidget from 'web.public.widget';
import 'website_sale_wishlist.wishlist';

publicWidget.registry.ProductWishlist.include({
    events: _.extend({}, publicWidget.registry.ProductWishlist.prototype.events, {
        'click .wishlist-section .o_notify_stock': '_onClickNotifyStock',
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Removes wishlist indication when adding a product to the wishlist.
     *
     * @override
     */
    _addNewProducts: function () {
        this._super(...arguments);
        const wishlistMessageEl = this.el.querySelector('#stock_wishlist_message');
        if (wishlistMessageEl) {
            wishlistMessageEl.classList.add('d-none');
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickNotifyStock: function (ev) {
        const targetEl = ev.currentTarget;
        const wishID = targetEl.closest('tr').dataset.wishId;
        const iconEl = targetEl.querySelector('i');
        const currentNotify = targetEl.dataset.notify === 'True';
        this._rpc({
            route: `/shop/wishlist/notify/${wishID}`,
            params: {
                notify: !currentNotify,
            }
        }).then((notify) => {
            targetEl.dataset.notify = notify ? 'True' : 'False';
            iconEl.classList.toggle('fa-check-square-o', notify);
            iconEl.classList.toggle('fa-square-o', !notify);
        });
    },
});
