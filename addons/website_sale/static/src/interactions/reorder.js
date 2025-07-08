import { browser } from '@web/core/browser/browser';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { redirect } from '@web/core/utils/urls';
import { Interaction } from '@web/public/interaction';

export class SaleOrderPortalReorder extends Interaction {
    static selector = '.o_portal_sidebar';
    dynamicContent = {
        'button.o_wsale_reorder_button': { 't-on-click': this.onReorder },
    };

    /**
     * Handles the reorder functionality when the reorder button is clicked.
     * Does the reorder by calling the `/my/orders/reorder` endpoint with the order ID and
     * access token.
     *
     * @param {Event} ev - The event triggered when the reorder button is clicked.
     */
    async onReorder(ev) {
        this.orderId = parseInt(ev.currentTarget.dataset.saleOrderId);
        this.accessToken = new URLSearchParams(window.location.search).get('access_token');
        if (!this.orderId || !this.accessToken) return;

        await this._doReorder();
    }

    async _doReorder() {
        try {
            const correctCartQty = await this.waitFor(rpc('/my/orders/reorder', {
                order_id: this.orderId,
                access_token: this.accessToken,
            }));

            // Sync cart quantity in session storage when adding reorder products from backend,
            // since `website_sale_cart_quantity` updates only via the cart service.
            browser.sessionStorage.setItem('website_sale_cart_quantity', correctCartQty);

            redirect('/shop/cart');
        } catch (error) {
            console.error("Error during reordering:", error);
        }
    }
}

registry
    .category('public.interactions')
    .add('website_sale.portal_reorder', SaleOrderPortalReorder);
