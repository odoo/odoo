odoo.define('point_of_sale.PaymentScreen', function(require) {
    'use strict';

    const { _t, qweb } = require('web.core');
    const { parse } = require('web.field_utils');
    const { is_email } = require('web.utils');
    const { PosComponent } = require('point_of_sale.PosComponent');
    const { Chrome } = require('point_of_sale.chrome');
    const { PaymentMethodButton } = require('point_of_sale.PaymentMethodButton');
    const { PaymentScreenNumpad } = require('point_of_sale.PaymentScreenNumpad');
    const { PaymentScreenPaymentLines } = require('point_of_sale.PaymentScreenPaymentLines');
    const { useNumberBuffer } = require('point_of_sale.custom_hooks');
    const { useListener } = require('web.custom_hooks');

    class PaymentScreen extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('delete-payment-line', this.deletePaymentLine);
            useListener('select-payment-line', this.selectPaymentLine);
            useListener('new-payment-line', this.addNewPaymentLine);
            useListener('update-selected-paymentline', this._updateSelectedPaymentline);
            useNumberBuffer({
                // The numberBuffer listens to this event to update its state.
                // Basically means 'update the buffer when this event is triggered'
                nonKeyboardEvent: 'input-from-numpad',
                // When the buffer is updated, trigger this event.
                // Note that the component listens to it.
                triggerAtInput: 'update-selected-paymentline',
            });
            this.payment_interface = null;
        }
        mounted() {
            this.env.pos.on(
                'change:selectedOrder',
                () => {
                    this.render();
                },
                this
            );
            this.currentOrder.on(
                'change',
                () => {
                    this.render();
                },
                this
            );
            this.currentOrder.paymentlines.on(
                'change',
                () => {
                    this.render();
                },
                this
            );
        }
        willUnmount() {
            this.env.pos.off('change:selectedOrder', null, this);
            this.currentOrder.off('change', null, this);
            this.currentOrder.paymentlines.off('change', null, this);
        }
        get currentOrder() {
            return this.env.pos.get_order();
        }
        get paymentLines() {
            return this.currentOrder.get_paymentlines();
        }
        get selectedPaymentLine() {
            return this.currentOrder.selected_paymentline;
        }
        async selectClient() {
            await this.showTempScreen('ClientListScreen');
        }
        addNewPaymentLine({ detail: paymentMethod}) {
            // original function: click_paymentmethods
            if (this.currentOrder.electronic_payment_in_progress()) {
                this.showPopup('ErrorPopup', {
                    title: _t('Error'),
                    body: _t('There is already an electronic payment in progress.'),
                });
                return false;
            } else {
                this.currentOrder.add_paymentline(paymentMethod);
                this.numberBuffer.reset();
                if (paymentMethod.payment_terminal) {
                    this.currentOrder.selected_paymentline.set_payment_status('pending');
                }
                return true;
            }
        }
        _updateSelectedPaymentline() {
            if (this.paymentLines.every(line => line.paid)) {
                this.currentOrder.add_paymentline(this.env.pos.payment_methods[0]);
            }
            if (!this.selectedPaymentLine) return; // do nothing if no selected payment line
            // disable changing amount on paymentlines with running or done payments on a payment terminal
            if (
                this.payment_interface &&
                !['pending', 'retry'].includes(this.selectedPaymentLine.get_payment_status())
            ) {
                return;
            }
            if (this.numberBuffer.get() === null) {
                this.deletePaymentLine({ detail: { cid: this.selectedPaymentLine.cid } });
            } else {
                this.selectedPaymentLine.set_amount(this.numberBuffer.getFloat());
            }
        }
        toggleIsToInvoice() {
            // click_invoice
            this.currentOrder.set_to_invoice(!this.currentOrder.is_to_invoice());
            this.render();
        }
        toggleIsToEmail() {
            // click_email
            this.currentOrder.set_to_email(!this.currentOrder.is_to_email());
            this.render();
        }
        openCashbox() {
            this.env.pos.proxy.printer.open_cashbox();
        }
        async addTip() {
            // click_tip
            const tip = this.currentOrder.get_tip();
            const change = this.currentOrder.get_change();
            let value = tip;

            if (tip === 0 && change > 0) {
                value = change;
            }

            const { confirmed, payload } = await this.showPopup('NumberPopup', {
                title: tip ? this.env._t('Change Tip') : this.env._t('Add Tip'),
                startingValue: value,
            });

            if (confirmed) {
                this.currentOrder.set_tip(parse.float(payload));
            }
        }
        deletePaymentLine(event) {
            const { cid } = event.detail;
            const line = this.paymentLines.find(line => line.cid === cid);

            // If a paymentline with a payment terminal linked to
            // it is removed, the terminal should get a cancel
            // request.
            if (['waiting', 'waitingCard', 'timeout'].includes(line.get_payment_status())) {
                line.payment_method.payment_terminal.send_payment_cancel(this.currentOrder, cid);
            }

            this.currentOrder.remove_paymentline(line);
            this.numberBuffer.reset();
            this.render();
        }
        selectPaymentLine(event) {
            const { cid } = event.detail;
            const line = this.paymentLines.find(line => line.cid === cid);
            this.currentOrder.select_paymentline(line);
            this.numberBuffer.reset();
            this.render();
        }
        async validateOrder(isForceValidate) {
            if (await this._isOrderValid(isForceValidate)) {
                // remove pending payments before finalizing the validation
                for (let line of this.paymentLines) {
                    if (!line.is_done()) this.currentOrder.remove_paymentline(line);
                }
                this._finalizeValidation();
            }
        }
        _finalizeValidation() {
            if (this.currentOrder.is_paid_with_cash() && this.env.pos.config.iface_cashdrawer) {
                this.env.pos.proxy.printer.open_cashbox();
            }

            this.currentOrder.initialize_validation_date();
            this.currentOrder.finalized = true;

            if (this.currentOrder.is_to_invoice()) {
                var invoiced = this.env.pos.push_and_invoice_order(this.currentOrder);
                this.invoicing = true;

                invoiced.catch(
                    () => {
                        this.trigger('show-screen', {
                            name: 'ReceiptScreen',
                            props: { printInvoiceIsShown: true },
                        });
                        console.log('TODO jcb: Error handler later');
                    }
                    // this._handleFailedPushOrder.bind(this, this.currentOrder, false)
                );

                invoiced.then(server_ids => {
                    this.invoicing = false;
                    this._postPushOrderResolve(this.currentOrder, server_ids)
                        .then(() => {
                            this.trigger('show-screen', { name: 'ReceiptScreen' });
                        })
                        .catch(error => {
                            this.trigger('show-screen', {
                                name: 'ReceiptScreen',
                                props: { printInvoiceIsShown: true },
                            });
                            if (error) {
                                this.showPopup('ErrorPopup', {
                                    title: 'Error: no internet connection',
                                    body: error,
                                });
                            }
                        });
                });
            } else {
                var ordered = this.env.pos.push_order(this.currentOrder);
                if (this.currentOrder.wait_for_push_order()) {
                    var server_ids = [];
                    ordered
                        .then(ids => {
                            server_ids = ids;
                        })
                        .finally(() => {
                            this._postPushOrderResolve(this.currentOrder, server_ids)
                                .then(() => {
                                    this.trigger('show-screen', { name: 'ReceiptScreen' });
                                })
                                .catch(error => {
                                    this.trigger('show-screen', { name: 'ReceiptScreen' });
                                    if (error) {
                                        this.showPopup('ErrorPopup', {
                                            title: 'Error: no internet connection',
                                            body: error,
                                        });
                                    }
                                });
                        });
                } else {
                    this.trigger('show-screen', { name: 'ReceiptScreen' });
                }
            }
        }
        async _isOrderValid(isForceValidate) {
            if (this.currentOrder.get_orderlines().length === 0) {
                this.showPopup('ErrorPopup', {
                    title: _t('Empty Order'),
                    body: _t(
                        'There must be at least one product in your order before it can be validated'
                    ),
                });
                return false;
            }

            if (!this.currentOrder.is_paid() || this.invoicing) {
                return false;
            }

            if (this.currentOrder.has_not_valid_rounding()) {
                var line = this.currentOrder.has_not_valid_rounding();
                this.showPopup('ErrorPopup', {
                    title: _t('Incorrect rounding'),
                    body: _t(
                        'You have to round your payments lines.' + line.amount + ' is not rounded.'
                    ),
                });
                return false;
            }

            // The exact amount must be paid if there is no cash payment method defined.
            if (
                Math.abs(
                    this.currentOrder.get_total_with_tax() - this.currentOrder.get_total_paid()
                ) > 0.00001
            ) {
                var cash = false;
                for (var i = 0; i < this.env.pos.payment_methods.length; i++) {
                    cash = cash || this.env.pos.payment_methods[i].is_cash_count;
                }
                if (!cash) {
                    this.showPopup('ErrorPopup', {
                        title: _t('Cannot return change without a cash payment method'),
                        body: _t(
                            'There is no cash payment method available in this point of sale to handle the change.\n\n Please pay the exact amount or add a cash payment method in the point of sale configuration'
                        ),
                    });
                    return false;
                }
            }

            var client = this.currentOrder.get_client();
            if (
                this.currentOrder.is_to_email() &&
                (!client || (client && !is_email(client.email)))
            ) {
                var title = !client ? 'Please select the customer' : 'Please provide valid email';
                var body = !client
                    ? 'You need to select the customer before you can send the receipt via email.'
                    : 'This customer does not have a valid email address, define one or do not send an email.';

                this.showPopup('ConfirmPopup', {
                    title: _t(title),
                    body: _t(body),
                }).then(({ confirmed }) => {
                    if (confirmed) this.trigger('show-screen', { name: 'ClientListScreen' });
                });

                return false;
            }

            // if the change is too large, it's probably an input error, make the user confirm.
            if (
                !isForceValidate &&
                this.currentOrder.get_total_with_tax() > 0 &&
                this.currentOrder.get_total_with_tax() * 1000 < this.currentOrder.get_total_paid()
            ) {
                this.showPopup('ConfirmPopup', {
                    title: _t('Please Confirm Large Amount'),
                    body:
                        _t('Are you sure that the customer wants to  pay') +
                        ' ' +
                        this.env.pos.format_currency(this.currentOrder.get_total_paid()) +
                        ' ' +
                        _t('for an order of') +
                        ' ' +
                        this.env.pos.format_currency(this.currentOrder.get_total_with_tax()) +
                        ' ' +
                        _t('? Clicking "Confirm" will validate the payment.'),
                }).then(({ confirmed }) => {
                    if (confirmed) this.validateOrder(true);
                });
                return false;
            }

            return true;
        }
        _getAmountString() {
            if (!this.selectedPaymentLine) return '';
            const amount = this.selectedPaymentLine.get_amount();
            const formattedAmount = this.env.pos.formatFixed(amount);
            return formattedAmount === '0' ? '' : formattedAmount;
        }
        _postPushOrderResolve(order, order_server_ids) {
            if (order.is_to_email()) {
                return this._sendReceiptToCustomer(order_server_ids);
            } else {
                return Promise.resolve();
            }
        }
        async _sendReceiptToCustomer(order_server_ids) {
            // TODO jcb: which QWeb will render?
            var order = this.env.pos.get_order();
            var data = {
                widget: this,
                pos: order.pos,
                order: order,
                receipt: order.export_for_printing(),
                orderlines: order.get_orderlines(),
                paymentlines: order.get_paymentlines(),
            };

            var receipt = qweb.render('OrderReceipt', data);
            var printer = new Printer();

            return new Promise(function(resolve, reject) {
                printer.htmlToImg(receipt).then(function(ticket) {
                    rpc.query({
                        model: 'pos.order',
                        method: 'action_receipt_to_customer',
                        args: [order_server_ids, order.get_name(), order.get_client(), ticket],
                    })
                        .then(function() {
                            resolve();
                        })
                        .catch(function() {
                            order.set_to_email(false);
                            reject(
                                'There is no internet connection, impossible to send the email.'
                            );
                        });
                });
            });
        }
    }
    PaymentScreen.components = {
        PaymentScreenNumpad,
        PaymentMethodButton,
        PaymentScreenPaymentLines,
    };

    Chrome.addComponents([PaymentScreen]);

    return { PaymentScreen };
});
