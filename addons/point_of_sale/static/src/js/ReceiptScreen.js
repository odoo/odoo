odoo.define('point_of_sale.ReceiptScreen', function(require) {
    'use strict';

    const core = require('web.core');
    const { PosComponent } = require('point_of_sale.PosComponent');
    const { OrderReceipt } = require('point_of_sale.OrderReceipt');

    const _t = core._t;

    class ReceiptScreen extends PosComponent {
        /**
         * Optional props:
         *     isShowPrintInvoice: Boolean
         */
        constructor() {
            super(...arguments);
            this.gui = this.props.gui;
            this.receiptRenderEnv = this._receiptRenderEnv();
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
            return this.env.pos.format_currency(this.currenOrder.get_change());
        }
        get currenOrder() {
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
            if (this._shouldAutoPrint() && !this.currenOrder.is_to_email()) {
                await this.onPrintReceipt();
                if (this._shouldCloseImmediately()) {
                    this.onOrderDone();
                }
            }
        }
        onOrderDone() {
            this.currenOrder.finalize();
            this.trigger('show-screen', { name: 'ProductScreen' });
        }
        async onPrintReceipt() {
            try {
                if (this.env.pos.proxy.printer) {
                    await this._printHtml();
                } else {
                    this._printWeb();
                }
                this.currenOrder._printed = true;
            } catch (error) {
                this.trigger('pos-error', { error });
            }
        }
        async onPrintInvoice() {
            // TODO jcb
            // We want the print invoice button to appear when there is a
            // syncing error when the receipt screen is shown.
        }
        _receiptRenderEnv() {
            // old name: get_receipt_render_env
            return {
                pos: this.env.pos,
                order: this.currenOrder,
                receipt: this.currenOrder.export_for_printing(),
                orderlines: this.currenOrder.get_orderlines(),
                paymentlines: this.currenOrder.get_paymentlines(),
            };
        }
        _shouldAutoPrint() {
            return this.env.pos.config.iface_print_auto && !this.currenOrder._printed;
        }
        _shouldCloseImmediately() {
            var invoiced_finalized = this.currenOrder.is_to_invoice()
                ? this.currenOrder.finalized
                : true;
            return (
                this.env.pos.proxy.printer &&
                this.env.pos.config.iface_print_skip_screen &&
                invoiced_finalized
            );
        }
        _printWeb() {
            if ($.browser.safari) {
                document.execCommand('print', false, null);
            } else {
                try {
                    window.print();
                } catch (err) {
                    if (navigator.userAgent.toLowerCase().indexOf('android') > -1) {
                        throw {
                            name: 'PrintingError',
                            message: {
                                title: _t('Printing is not supported on some android browsers'),
                                body: _t(
                                    'Printing is not supported on some android browsers due to no default printing protocol ' +
                                        'is available. It is possible to print your tickets by making use of an IoT Box.'
                                ),
                            },
                        };
                    } else {
                        throw err;
                    }
                }
            }
        }
        async _printHtml() {
            const orderReceipt = this.env.qweb.render('OrderReceipt', {
                pos: this.env.pos,
                receiptEnv: this.receiptRenderEnv,
            });
            // Important to await because we want to catch the error
            await this.env.pos.proxy.printer.print_receipt(orderReceipt);
        }
    }
    ReceiptScreen.components = { OrderReceipt };

    // register screen component
    const { Chrome } = require('point_of_sale.chrome');
    Chrome.addComponents([ReceiptScreen]);

    return { ReceiptScreen };
});
