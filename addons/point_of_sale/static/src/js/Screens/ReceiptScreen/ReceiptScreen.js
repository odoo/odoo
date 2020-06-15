odoo.define('point_of_sale.ReceiptScreen', function (require) {
    'use strict';

    const { useState } = owl.hooks;
    const { useErrorHandlers, onChangeOrder } = require('point_of_sale.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const AbstractReceiptScreen = require('point_of_sale.AbstractReceiptScreen');

    const ReceiptScreen = (AbstractReceiptScreen) => {
        class ReceiptScreen extends AbstractReceiptScreen {
            /**
             * Optional props:
             *     printInvoiceIsShown: Boolean
             */
            constructor() {
                super(...arguments);
                useErrorHandlers();
                onChangeOrder(null, (newOrder) => newOrder && this.render());
                this.state = useState({ printInvoiceIsShown: this.props.printInvoiceIsShown });
            }
            mounted() {
                // Here, we send a task to the event loop that handles
                // the printing of the receipt when the component is mounted.
                // We are doing this because we want the receipt screen to be
                // displayed regardless of what happen to the handleAutoPrint
                // call.
                setTimeout(async () => await this.handleAutoPrint(), 0);
            }
            get change() {
                return this.env.pos.format_currency(this.currentOrder.get_change());
            }
            get currentOrder() {
                return this.env.pos.get_order();
            }
            get nextScreen() {
                return { name: 'ProductScreen' };
            }
            /**
             * This function is called outside the rendering call stack. This way,
             * we don't block the displaying of ReceiptScreen when it is mounted; additionally,
             * any error that can happen during the printing does not affect the rendering.
             */
            async handleAutoPrint() {
                if (this._shouldAutoPrint() && !this.currentOrder.is_to_email()) {
                    await this.printReceipt();
                    if (this.currentOrder._printed && this._shouldCloseImmediately()) {
                        this.orderDone();
                    }
                }
            }
            orderDone() {
                this.currentOrder.finalize();
                const { name, props } = this.nextScreen;
                this.showScreen(name, props);
            }
            async printReceipt() {
                const isPrinted = await this._printReceipt();
                if (isPrinted) {
                    this.currentOrder._printed = true;
                }
            }
            async onPrintInvoice() {
                // The button element of this event handler appears when the order
                // failed to sync and is to be invoiced. What we do here is to try
                // to sync again to eventually print the invoice.
                try {
                    await this.env.pos.push_and_invoice_order(this.currentOrder);
                    this.state.printInvoiceIsShown = false;
                } catch (error) {
                    if (error instanceof Error) {
                        throw error;
                    } else {
                        await this._handlePushOrderError(error);
                    }
                }
            }
            _shouldAutoPrint() {
                return this.env.pos.config.iface_print_auto && !this.currentOrder._printed;
            }
            _shouldCloseImmediately() {
                var invoiced_finalized = this.currentOrder.is_to_invoice() ? this.currentOrder.finalized : true;
                return this.env.pos.proxy.printer && this.env.pos.config.iface_print_skip_screen && invoiced_finalized;
            }
        }
        ReceiptScreen.template = 'ReceiptScreen';
        return ReceiptScreen;
    };

    Registries.Component.addByExtending(ReceiptScreen, AbstractReceiptScreen);

    return ReceiptScreen;
});
