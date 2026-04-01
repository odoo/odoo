import { cookie } from '@web/core/browser/cookie';
import { rpc } from '@web/core/network/rpc';
import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';

export class RecentlyViewedProducts extends Interaction {
    static selector = '.o_wsale_product_page';
    dynamicContent = {
        'input.product_id[name="product_id"]': {
            't-on-change.withTarget': this.debounced(this.onProductChange, 500),
        },
    };

    /**
     * Mark the product as viewed.
     *
     * @param {Event} ev
     * @param {HTMLElement} currentTargetEl
     */
    async onProductChange(ev, currentTargetEl) {
        if (!parseInt(this.el.querySelector('#product_detail').dataset.viewTrack)) {
            return; // Product not tracked.
        }
        const productId = parseInt(currentTargetEl.value);
        const cookieName = 'seen_product_id_' + productId;
        if (cookie.get(cookieName)) {
            return; // Product already tracked in the last 30 min.
        }
        if (this.el.querySelector('.js_product.css_not_available')) {
            return; // Product not available.
        }
        await this.waitFor(rpc('/shop/products/recently_viewed_update', {
            product_id: productId,
        }));
        cookie.set(cookieName, productId, 30 * 60, 'optional');
    }
}

registry
    .category('public.interactions')
    .add('website_sale.recently_viewed_products', RecentlyViewedProducts);
