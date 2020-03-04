odoo.define('point_of_sale.ReceiptScreen', function(require) {
    'use strict';

    const core = require('web.core');
    const { Chrome } = require('point_of_sale.chrome');
    const { useRef, useState } = owl.hooks;
    const { PosComponent, addComponents } = require('point_of_sale.PosComponent');
    const { OrderReceipt } = require('point_of_sale.OrderReceipt');
    const { useErrorHandlers } = require('point_of_sale.custom_hooks');

    const _t = core._t;

    class ReceiptScreen extends PosComponent {
        /**
         * Optional props:
         *     printInvoiceIsShown: Boolean
         */
        constructor() {
            super(...arguments);
            useErrorHandlers();
            this.state = useState({ printInvoiceIsShown: this.props.printInvoiceIsShown });
            this.orderReceipt = useRef('order-receipt');
        }
        mounted() {
            this.env.pos.on(
                'change:selectedOrder',
                () => {
                    this.render();
                },
                this
            );
            // Here, we send a task to the event loop that handles
            // the printing of the receipt when the component is mounted.
            // We are doing this because we want the receipt screen to be
            // displayed regardless of what happen to the handleAutoPrint
            // call.
            setTimeout(async () => await this.handleAutoPrint(), 0);
        }
        willUnmount() {
            this.env.pos.off('change:selectedOrder', null, this);
        }
        get change() {
            return this.env.pos.format_currency(this.currentOrder.get_change());
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        /**
         * This function is called outside the rendering call stack. This way,
         * we don't block the displaying of ReceiptScreen when it is mounted; additionally,
         * any error that can happen during the printing does not affect the rendering.
         * Nevertheless, we still wanted to handle error in generic way -- that
         * we make the parent component aware of any error and it is responsible of
         * showing the right error message.Thus, instead of throwing the error, we trigger an
         * event (an error event) that will be properly handled in Chrome Component.
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
            this.trigger('show-screen', { name: 'ProductScreen' });
        }
        async printReceipt() {
            if (this.env.pos.proxy.printer) {
                const printResult = await this.env.pos.proxy.printer.print_receipt(
                    this.orderReceipt.el.outerHTML
                );
                if (printResult.successful) {
                    this.currentOrder._printed = true;
                } else {
                    await this.showPopup('ErrorPopup', {
                        title: printResult.message.title,
                        body: printResult.message.body,
                    });
                }
            } else {
                await this._printWeb();
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
            var invoiced_finalized = this.currentOrder.is_to_invoice()
                ? this.currentOrder.finalized
                : true;
            return (
                this.env.pos.proxy.printer &&
                this.env.pos.config.iface_print_skip_screen &&
                invoiced_finalized
            );
        }
        async _printWeb() {
            if ($.browser.safari) {
                document.execCommand('print', false, null);
            } else {
                try {
                    window.print();
                    this.currentOrder._printed = true;
                } catch (err) {
                    if (navigator.userAgent.toLowerCase().indexOf('android') > -1) {
                        await this.showPopup('ErrorPopup', {
                            title: _t('Printing is not supported on some android browsers'),
                            body: _t(
                                'Printing is not supported on some android browsers due to no default printing protocol ' +
                                    'is available. It is possible to print your tickets by making use of an IoT Box.'
                            ),
                        });
                    } else {
                        throw err;
                    }
                }
            }
        }
    }
    ReceiptScreen.components = { OrderReceipt };

    // register screen component
    addComponents(Chrome, [ReceiptScreen]);

    return { ReceiptScreen };
});
