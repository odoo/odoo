import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { registry } from '@web/core/registry';
import { ConfirmationDialog } from '@web/core/confirmation_dialog/confirmation_dialog';
import { Interaction } from '@web/public/interaction';

export class SaleOrderPortalReorder extends Interaction {
    static selector = ".o_portal_sidebar";
    dynamicContent = {
        'button.o_wsale_reorder_button': { 't-on-click': async (ev) => await this._onReorder(ev) },
    };

    /**
     * Handles the reorder functionality when the reorder button is clicked.
     * Fetches the reorder content and products associated with the order and proceeds to 
     * check if the cart needs updating or products need to be added to the cart.
     * 
     * @param {Event} ev - The event triggered when the reorder button is clicked.
     */
    async _onReorder(ev) {
        this.orderId = parseInt(ev.currentTarget.dataset.saleOrderId);
        this.accessToken = new URLSearchParams(window.location.search).get('access_token');
        if (!this.orderId || !this.accessToken) return;

        const cartQty = await rpc('/shop/cart/quantity');
        if (cartQty) {
            sessionStorage.setItem('website_sale_cart_quantity', cartQty);
            await this._showConfirmationDialog();
        } else {
            await this._doReorder();
        }
    }

    async _showConfirmationDialog() {
        this.services.dialog.add(ReorderConfirmationDialog, {
            body: _t("Do you wish to clear your cart before adding products to it?"),
            confirm: async () => {
                await rpc('/shop/cart/clear');
                await this._doReorder();
            },
            cancel: async () => {
                await this._doReorder();
            },
        });
    }

    async _doReorder() {
        try {
            await rpc('/my/orders/reorder', {
                order_id: this.orderId,
                access_token: this.accessToken
            });
            window.location = '/shop/cart';
        } catch (error) {
            console.error('Error during reordering:', error);
        }
    }
}

export class ReorderConfirmationDialog extends ConfirmationDialog {
    static template = 'website_sale.ReorderConfirmationDialog';
}

registry
    .category('public.interactions')
    .add('website_sale.SaleOrderPortalReorder', SaleOrderPortalReorder);
