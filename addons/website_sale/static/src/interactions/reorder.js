import { browser } from '@web/core/browser/browser';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { redirect } from '@web/core/utils/urls';
import { Interaction } from '@web/public/interaction';

export class SaleOrderPortalReorder extends Interaction {
    static selector = '#sale_order_sidebar_button';
    dynamicContent = {
        'button#reorder_sidebar_button': { 't-on-click': this.onReorder },
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
        if (!this.orderId) return;

        await this._doReorder();
    }

    async _doReorder() {
        try {
            const values = await this.waitFor(rpc('/my/orders/reorder', {
                order_id: this.orderId,
                access_token: this.accessToken,
            }));

            // Sync cart quantity in session storage when adding reorder products from backend,
            // since `website_sale_cart_quantity` updates only via the cart service.
            browser.sessionStorage.setItem('website_sale_cart_quantity', values.cart_quantity);

            this._trackProducts(values.tracking_info);
            redirect('/shop/cart');
        } catch (error) {
            console.error("Error during reordering:", error);
        }
    }

    /**
     * Track the products added to the cart.
     *
     * @private
     * @param {Object[]} trackingInfo - A list of product tracking information.
     *
     * @returns {void}
     */
    _trackProducts(trackingInfo) {
        document.querySelector('.oe_website_sale').dispatchEvent(
            new CustomEvent('add_to_cart_event', {'detail': trackingInfo})
        );
    }
}

registry
    .category('public.interactions')
    .add('website_sale.portal_reorder', SaleOrderPortalReorder);
