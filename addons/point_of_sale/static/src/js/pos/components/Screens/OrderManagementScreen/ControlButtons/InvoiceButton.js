/** @odoo-module alias=point_of_sale.InvoiceButton **/

import { useListener } from 'web.custom_hooks';
import { isRpcError } from 'point_of_sale.utils';
import PosComponent from 'point_of_sale.PosComponent';

class InvoiceButton extends PosComponent {
    constructor() {
        super(...arguments);
        useListener('click', this._onClick);
    }
    get selectedOrder() {
        return this.props.activeOrder;
    }
    get isAlreadyInvoiced() {
        if (!this.selectedOrder) return false;
        return Boolean(this.selectedOrder.account_move);
    }
    get commandName() {
        if (!this.selectedOrder) {
            return 'Invoice';
        } else {
            return this.isAlreadyInvoiced
                ? 'Reprint Invoice'
                : this.selectedOrder._extras.isFromClosedSession
                ? 'Cannot Invoice'
                : 'Invoice';
        }
    }
    get isHighlighted() {
        return this.selectedOrder && !this.isAlreadyInvoiced && !this.selectedOrder._extras.isFromClosedSession;
    }
    async _downloadInvoice(orderId) {
        try {
            await this.env.model.webClient.do_action('point_of_sale.pos_invoice_report', {
                additional_context: {
                    active_ids: [orderId],
                },
            });
        } catch (error) {
            if (error instanceof Error) {
                throw error;
            } else {
                // NOTE: error here is most probably undefined
                this.env.ui.askUser('ErrorPopup', {
                    title: this.env._t('Network Error'),
                    body: this.env._t('Unable to download invoice.'),
                });
            }
        }
    }
    async _invoiceOrder() {
        const order = this.selectedOrder;
        if (!order) return;

        // Part 0.1. If already invoiced, print the invoice.
        if (this.isAlreadyInvoiced) {
            await this._downloadInvoice(order.id);
            return;
        }

        // Part 0.2. Check if order belongs to an active session.
        // If not, do not allow invoicing.
        if (order._extras.isFromClosedSession) {
            this.env.ui.askUser('ErrorPopup', {
                title: this.env._t('Session is closed'),
                body: this.env._t('Cannot invoice order from closed session.'),
            });
            return;
        }

        // Part 1: Handle missing client.
        // Write to pos.order the selected client.
        if (!order.partner_id) {
            const confirmedPopup = await this.env.ui.askUser('ConfirmPopup', {
                title: 'Need customer to invoice',
                body: 'Do you want to open the customer list to select customer?',
            });
            if (!confirmedPopup) return;

            const [confirmedTempScreen, newClientId] = await this.showTempScreen('ClientListScreen');
            if (!confirmedTempScreen) return;

            await this.rpc({
                model: 'pos.order',
                method: 'write',
                args: [[order.id], { partner_id: newClientId }],
                kwargs: { context: this.env.session.user_context },
            });
        }

        // Part 2: Invoice the order.
        await this.rpc(
            {
                model: 'pos.order',
                method: 'action_pos_order_invoice',
                args: [order.id],
                kwargs: { context: this.env.session.user_context },
            },
            {
                timeout: 30000,
                shadow: true,
            }
        );

        // Part 3: Download invoice.
        await this._downloadInvoice(order.id);

        // Invalidate the cache then fetch the updated order.
        this.env.model.orderFetcher.invalidateCache([order.id]);
        await this.env.model.orderFetcher.fetch();
        this.env.model.actionHandler({ name: 'actionSelectOrder', args: [this.selectedOrder] });
    }
    async _onClick() {
        try {
            await this._invoiceOrder();
        } catch (error) {
            if (isRpcError(error) && error.message.code < 0) {
                this.env.ui.askUser('ErrorPopup', {
                    title: this.env._t('Network Error'),
                    body: this.env._t('Unable to invoice order.'),
                });
            } else {
                throw error;
            }
        }
    }
}
InvoiceButton.template = 'point_of_sale.InvoiceButton';

export default InvoiceButton;
