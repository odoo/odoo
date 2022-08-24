/** @odoo-module **/

import publicWidget from 'web.public.widget';
import 'website_sale_wishlist.wishlist';

publicWidget.registry.ProductWishlist.include({

    /**
     * Removes wishlist indication when adding a product to the wishlist.
     *
     * @override
     */
    _addNewProducts: function () {
        this._super(...arguments);
        const saveForLaterButtonEl = document.querySelector('#wsale_save_for_later_button');
        const addedToYourWishListAlertEl = document.querySelector('#wsale_added_to_your_wishlist_alert');
        if (saveForLaterButtonEl) {
            saveForLaterButtonEl.classList.add('d-none');
            addedToYourWishListAlertEl.classList.remove('d-none');
        }
    },
});
