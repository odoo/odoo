odoo.define('point_of_sale.InvoiceButton', function (require) {
    'use strict';

    const { useListener } = require('web.custom_hooks');
    const { useContext } = owl.hooks;
    const { isRpcError } = require('point_of_sale.utils');
    const PosComponent = require('point_of_sale.PosComponent');
    const OrderManagementScreen = require('point_of_sale.OrderManagementScreen');
    const OrderFetcher = require('point_of_sale.OrderFetcher');
    const Registries = require('point_of_sale.Registries');
    const contexts = require('point_of_sale.PosContext');

    class InvoiceButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this._onClick);
            this.orderManagementContext = useContext(contexts.orderManagement);
        }
        get selectedOrder() {
            return this.orderManagementContext.selectedOrder;
        }
        set selectedOrder(value) {
            this.orderManagementContext.selectedOrder = value;
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
                    : this.selectedOrder.isFromClosedSession
                    ? 'Cannot Invoice'
                    : 'Invoice';
            }
        }
        get isHighlighted() {
            return this.selectedOrder && !this.isAlreadyInvoiced && !this.selectedOrder.isFromClosedSession;
        }
        async _downloadInvoice(orderId) {
            try {
                await this.env.pos.do_action('point_of_sale.pos_invoice_report', {
                    additional_context: {
                        active_ids: [orderId],
                    },
                });
            } catch (error) {
                if (error instanceof Error) {
                    throw error;
                } else {
                    // NOTE: error here is most probably undefined
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Network Error'),
                        body: this.env._t('Unable to download invoice.'),
                    });
                }
            }
        }
        async _invoiceOrder() {
            const order = this.selectedOrder;
            if (!order) return;

            const orderId = order.backendId;

            // Part 0.1. If already invoiced, print the invoice.
            if (this.isAlreadyInvoiced) {
                await this._downloadInvoice(orderId);
                return;
            }

            // Part 0.2. Check if order belongs to an active session.
            // If not, do not allow invoicing.
            if (order.isFromClosedSession) {
                this.showPopup('ErrorPopup', {
                    title: this.env._t('Session is closed'),
                    body: this.env._t('Cannot invoice order from closed session.'),
                });
                return;
            }

            // Part 1: Handle missing client.
            // Write to pos.order the selected client.
            if (!order.get_client()) {
                const { confirmed: confirmedPopup } = await this.showPopup('ConfirmPopup', {
                    title: 'Need customer to invoice',
                    body: 'Do you want to open the customer list to select customer?',
                });
                if (!confirmedPopup) return;

                const { confirmed: confirmedTempScreen, payload: newClient } = await this.showTempScreen(
                    'ClientListScreen'
                );
                if (!confirmedTempScreen) return;

                await this.rpc({
                    model: 'pos.order',
                    method: 'write',
                    args: [[orderId], { partner_id: newClient.id }],
                    kwargs: { context: this.env.session.user_context },
                });
            }

            // Part 2: Invoice the order.
            await this.rpc(
                {
                    model: 'pos.order',
                    method: 'action_pos_order_invoice',
                    args: [orderId],
                    kwargs: { context: this.env.session.user_context },
                },
                {
                    timeout: 30000,
                    shadow: true,
                }
            );

            // Part 3: Download invoice.
            await this._downloadInvoice(orderId);

            // Invalidate the cache then fetch the updated order.
            OrderFetcher.invalidateCache([orderId]);
            await OrderFetcher.fetch();
            this.selectedOrder = OrderFetcher.get(this.selectedOrder.backendId);
        }
        async _onClick() {
            try {
                await this._invoiceOrder();
            } catch (error) {
                if (isRpcError(error) && error.message.code < 0) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Network Error'),
                        body: this.env._t('Unable to invoice order.'),
                    });
                } else {
                    throw error;
                }
            }
        }
    }
    InvoiceButton.template = 'InvoiceButton';

    OrderManagementScreen.addControlButton({
        component: InvoiceButton,
        condition: function () {
            return this.env.pos.config.module_account;
        },
    });

    Registries.Component.add(InvoiceButton);

    return InvoiceButton;
});
