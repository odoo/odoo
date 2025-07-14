import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc } from '@web/core/network/rpc';
import wishlistUtils from '@website_sale_wishlist/js/website_sale_wishlist_utils';

export class WishlistNavbar extends Interaction {
    static selector = '.o_wsale_my_wish';

    /**
     * Refresh the products in the wishlist.
     */
    async willStart() {
        const wishCount = parseInt(this.el.querySelector('.my_wish_quantity')?.textContent);
        if (wishlistUtils.getWishlistProductIds().length !== wishCount) {
            wishlistUtils.setWishlistProductIds(
                await this.waitFor(rpc('/shop/wishlist/get_product_ids'))
            );
        }
    }

    /**
     * Update the wishlist navbar.
     */
    start() {
        wishlistUtils.updateWishlistNavBar();
    }
}

registry
    .category('public.interactions')
    .add('website_sale_wishlist.wishlist_navbar', WishlistNavbar);
