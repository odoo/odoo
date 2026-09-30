import { patch } from '@web/core/utils/patch';
import {
    AddProductToWishlistButton
} from '@website_sale_wishlist/interactions/add_product_to_wishlist_button';

// TODO(loti): this doesn't work since interactions aren't restarted when the "save for later"
// button is appended to the template. It will be fixed once the variant mixin has been removed.
patch(AddProductToWishlistButton.prototype, {
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
