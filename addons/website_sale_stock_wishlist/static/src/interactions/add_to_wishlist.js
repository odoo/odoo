import { patch } from '@web/core/utils/patch';
import { AddToWishlist } from '@website_sale_wishlist/interactions/add_to_wishlist';

patch(AddToWishlist.prototype, {
    /**
     * Remove wishlist indication when adding a product to the wishlist.
     */
    async addProduct(ev) {
        await this.waitFor(super.addProduct(...arguments));
        const saveForLaterButton = document.querySelector('#wsale_save_for_later_button');
        const addedToWishListAlert = document.querySelector('#wsale_added_to_your_wishlist_alert');
        if (saveForLaterButton) {
            saveForLaterButton.classList.add('d-none');
            addedToWishListAlert.classList.remove('d-none');
        }
    },
});
