import { _t } from '@web/core/l10n/translation';
import { browser } from '@web/core/browser/browser';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { Interaction } from '@web/public/interaction';

export class SaleOrderPortalReorder extends Interaction {
    static selector = ".o_portal_sidebar";
    dynamicContent = {
        'button.o_wsale_reorder_button': { 't-on-click': this.onReorder },
    };

    /**
     * Handles the reorder functionality when the reorder button is clicked.
     * Fetches the reorder content and products associated with the order and proceeds to
     * check if the cart needs updating or products need to be added to the cart.
     *
     * @param {Event} ev - The event triggered when the reorder button is clicked.
     */
    async onReorder(ev) {
        this.orderId = parseInt(ev.currentTarget.dataset.saleOrderId);
        this.accessToken = new URLSearchParams(window.location.search).get('access_token');
        if (!this.orderId || !this.accessToken) return;

        const cartQty = parseInt(sessionStorage.getItem('website_sale_cart_quantity'));
        if (cartQty) {
            await this._showConfirmationDialog();
        } else {
            await this._doReorder();
        }
    }

    async _showConfirmationDialog() {
        this.services.dialog.add(ReorderConfirmationDialog, {
            body: _t("Do you wish to clear your cart before adding products to it?"),
            confirm: async () => {
                await this.waitFor(rpc('/shop/cart/clear'));
                await this._doReorder();
            },
            cancel: async () => {
                await this._doReorder();
            },
            dismiss: () => {},
        });
    }

    async _doReorder() {
        try {
            await this.waitFor(rpc('/my/orders/reorder', {
                order_id: this.orderId,
                access_token: this.accessToken
            }));
            window.location = '/shop/cart';
        } catch (error) {
            console.error('Error during reordering:', error);
        }
        // Sync cart quantity in session storage when adding reorder products from backend,
        // since `website_sale_cart_quantity` updates only via the cart service.
        const correctCartQty = await this.waitFor(rpc('/shop/cart/quantity'));
        browser.sessionStorage.setItem('website_sale_cart_quantity', correctCartQty);
    }
}

export class ReorderConfirmationDialog extends ConfirmationDialog {
    static template = 'website_sale.ReorderConfirmationDialog';
}

registry
    .category('public.interactions')
    .add('website_sale.SaleOrderPortalReorder', SaleOrderPortalReorder);
