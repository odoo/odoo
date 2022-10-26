odoo.define('point_of_sale.InvoiceButton', function (require) {
    'use strict';

    const { useListener } = require("@web/core/utils/hooks");
    const { isConnectionError } = require('point_of_sale.utils');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class InvoiceButton extends PosComponent {
        setup() {
            super.setup();
            useListener('click', this._onClick);
        }
        get isAlreadyInvoiced() {
            if (!this.props.order) return false;
            return Boolean(this.props.order.account_move);
        }
        get commandName() {
            if (!this.props.order) {
                return this.env._t('Invoice');
            } else {
                return this.isAlreadyInvoiced
                    ? this.env._t('Reprint Invoice')
                    : this.env._t('Invoice');
            }
        }
        async _downloadInvoice(orderId) {
            try {
                const [orderWithInvoice] = await this.rpc({
                    method: 'read',
                    model: 'pos.order',
                    args: [orderId, ['account_move']],
                    kwargs: { load: false },
                });
                if (orderWithInvoice && orderWithInvoice.account_move) {
                    await this.env.legacyActionManager.do_action('account.account_invoices', {
                        additional_context: {
                            active_ids: [orderWithInvoice.account_move],
                        },
                    });
                }
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
            const order = this.props.order;
            if (!order) return;

            const orderId = order.backendId;

            // Part 0. If already invoiced, print the invoice.
            if (this.isAlreadyInvoiced) {
                await this._downloadInvoice(orderId);
                return;
            }

            // Part 1: Handle missing partner.
            // Write to pos.order the selected partner.
            if (!order.get_partner()) {
                const { confirmed: confirmedPopup } = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Need customer to invoice'),
                    body: this.env._t('Do you want to open the customer list to select customer?'),
                });
                if (!confirmedPopup) return;

                const { confirmed: confirmedTempScreen, payload: newPartner } = await this.showTempScreen(
                    'PartnerListScreen'
                );
                if (!confirmedTempScreen) return;

                await this.rpc({
                    model: 'pos.order',
                    method: 'write',
                    args: [[orderId], { partner_id: newPartner.id }],
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
            this.trigger('order-invoiced', orderId);
        }
        async _onClick() {
            try {
                this.el.style.pointerEvents = 'none';
                await this._invoiceOrder();
            } catch (error) {
                if (isConnectionError(error)) {
                    this.showPopup('ErrorPopup', {
                        title: this.env._t('Network Error'),
                        body: this.env._t('Unable to invoice order.'),
                    });
                } else {
                    throw error;
                }
            } finally {
                this.el.style.pointerEvents = 'auto';
            }
        }
    }
    InvoiceButton.template = 'InvoiceButton';
    Registries.Component.add(InvoiceButton);

    return InvoiceButton;
});
