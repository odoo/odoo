import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { redirect } from '@web/core/utils/urls';
import { Interaction } from '@web/public/interaction';
import wishlistUtils from '@website_sale_wishlist/js/website_sale_wishlist_utils';

export class WishlistPage extends Interaction {
    static selector = '.o_wsale_wishlist_page';
    dynamicContent = {
        '.o_wish_rm': { 't-on-click': this.removeProduct },
        'button[name="add_to_cart"]': { 't-on-product_added_to_cart': this.removeProduct },
    };

    /**
     * Remove a product from the wishlist.
     *
     * @param {Event} ev
     */
    async removeProduct(ev) {
        const article = ev.currentTarget.closest('[name="wishlist_item"]');
        const wish = article.dataset.wishId;
        const productId = parseInt(article.dataset.productId);

        await this.waitFor(rpc(`/shop/wishlist/remove/${wish}`));
        article.style.display = 'none';

        wishlistUtils.removeWishlistProduct(productId);
        wishlistUtils.updateWishlistView();
        if (!wishlistUtils.getWishlistProductIds().length) {
            redirect(ev.type === 'product_added_to_cart' ? '/shop/cart' : '/shop');
        }
        wishlistUtils.updateWishlistNavBar();
    }
}

registry
    .category('public.interactions')
    .add('website_sale_wishlist.wishlist_page', WishlistPage);
