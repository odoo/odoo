odoo.define('point_of_sale.PaymentScreen', function(require) {
    'use strict';

    const { _t, qweb } = require('web.core');
    const { parse } = require('web.field_utils');
    const { PosComponent } = require('point_of_sale.PosComponent');
    const { Chrome } = require('point_of_sale.chrome');
    const { PaymentMethodButton } = require('point_of_sale.PaymentMethodButton');
    const { PaymentScreenNumpad } = require('point_of_sale.PaymentScreenNumpad');
    const { PaymentScreenPaymentLines } = require('point_of_sale.PaymentScreenPaymentLines');

    class PaymentScreen extends PosComponent {
        constructor() {
            super(...arguments);
            this.pos = this.props.pos;
            this.gui = this.props.gui;
            this.inputBuffer = '';
            this.isFirstInput = true;
            this.decimalPoint = _t.database.parameters.decimal_point;
            this.payment_interface = null;
        }
        mounted() {
            this.pos.on(
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
            this.pos.off('change:selectedOrder', null, this);
            this.currentOrder.off('change', null, this);
            this.currentOrder.paymentlines.off('change', null, this);
        }
        get currentOrder() {
            return this.pos.get_order();
        }
        get paymentLines() {
            return this.currentOrder.get_paymentlines();
        }
        get selectedPaymentLine() {
            return this.currentOrder.selected_paymentline;
        }
        addNewPaymentLine(paymentMethod) {
            // original function: click_paymentmethods
            if (this.currentOrder.electronic_payment_in_progress()) {
                this.gui.show_popup('error', {
                    title: _t('Error'),
                    body: _t('There is already an electronic payment in progress.'),
                });
                return false;
            } else {
                this.currentOrder.add_paymentline(paymentMethod);
                this._resetInput();
                if (paymentMethod.payment_terminal) {
                    this.currentOrder.selected_paymentline.set_payment_status('pending');
                }
                return true;
            }
        }
        inputFromNumpad(event) {
            const { value } = event.detail;

            if (this.paymentLines.every(line => line.paid)) {
                this.currentOrder.add_paymentline(this.pos.payment_methods[0]);
            }

            // disable changing amount on paymentlines with running or done payments on a payment terminal
            if (
                this.payment_interface &&
                !['pending', 'retry'].includes(this.selectedPaymentLine.get_payment_status())
            ) {
                return;
            }

            const newbuf = this.gui.numpad_input(this.inputBuffer, value, {
                firstinput: this.isFirstInput,
            });

            this.isFirstInput = newbuf.length === 0;

            // popup block inputs to prevent sneak editing.
            if (this.gui.has_popup()) {
                return;
            }

            if (newbuf !== this.inputBuffer) {
                this.inputBuffer = newbuf;
                if (this.selectedPaymentLine) {
                    let amount = this.inputBuffer;
                    if (this.inputBuffer !== '-') {
                        amount = parse.float(this.inputBuffer);
                    }
                    this.selectedPaymentLine.set_amount(amount);
                }
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
            this.pos.proxy.printer.open_cashbox();
        }
        addTip() {
            // click_tip
            const self = this;
            const tip = this.currentOrder.get_tip();
            const change = this.currentOrder.get_change();
            let value = tip;

            if (tip === 0 && change > 0) {
                value = change;
            }

            this.gui.show_popup('number', {
                title: tip ? _t('Change Tip') : _t('Add Tip'),
                value: this.pos.format_currency_no_symbol(value),
                confirm: value => {
                    self.currentOrder.set_tip(parse.float(value));
                },
            });
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
            this._resetInput();
            this.render();
        }
        selectPaymentLine(event) {
            const { cid } = event.detail;
            const line = this.paymentLines.find(line => line.cid === cid);
            this.currentOrder.select_paymentline(line);
            this._resetInput();
            this.render();
        }
        validateOrder() {
            if (this._isOrderValid()) {
                // remove pending payments before finalizing the validation
                for (let line of this.paymentLines) {
                    if (!line.is_done()) this.currentOrder.remove_paymentline(line);
                }
                this._finalizeValidation();
            }
        }
        _finalizeValidation() {
            if (this.currentOrder.is_paid_with_cash() && this.pos.config.iface_cashdrawer) {
                this.pos.proxy.printer.open_cashbox();
            }

            this.currentOrder.initialize_validation_date();
            this.currentOrder.finalized = true;

            if (this.currentOrder.is_to_invoice()) {
                var invoiced = this.pos.push_and_invoice_order(this.currentOrder);
                this.invoicing = true;

                invoiced.catch(
                    () => {
                        this.trigger('show-screen', {
                            name: 'ReceiptScreen',
                            props: { isShowPrintInvoice: true },
                        });
                        console.log('TODO jcb: Error handler later');
                    }
                    // this._handleFailedPushForInvoice.bind(this, this.currentOrder, false)
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
                                props: { isShowPrintInvoice: true },
                            });
                            if (error) {
                                this.gui.show_popup('error', {
                                    title: 'Error: no internet connection',
                                    body: error,
                                });
                            }
                        });
                });
            } else {
                var ordered = this.pos.push_order(this.currentOrder);
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
                                        this.gui.show_popup('error', {
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
        _isOrderValid(isForceValidate) {
            var self = this;

            if (this.currentOrder.get_orderlines().length === 0) {
                this.gui.show_popup('error', {
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
                this.gui.show_popup('error', {
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
                for (var i = 0; i < this.pos.payment_methods.length; i++) {
                    cash = cash || this.pos.payment_methods[i].is_cash_count;
                }
                if (!cash) {
                    this.gui.show_popup('error', {
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
                (!client || (client && !utils.is_email(client.email)))
            ) {
                var title = !client ? 'Please select the customer' : 'Please provide valid email';
                var body = !client
                    ? 'You need to select the customer before you can send the receipt via email.'
                    : 'This customer does not have a valid email address, define one or do not send an email.';
                this.gui.show_popup('confirm', {
                    title: _t(title),
                    body: _t(body),
                    confirm: function() {
                        this.trigger('show-screen', { name: 'ClientListScreen' });
                    },
                });
                return false;
            }

            // if the change is too large, it's probably an input error, make the user confirm.
            if (
                !isForceValidate &&
                this.currentOrder.get_total_with_tax() > 0 &&
                this.currentOrder.get_total_with_tax() * 1000 < this.currentOrder.get_total_paid()
            ) {
                this.gui.show_popup('confirm', {
                    title: _t('Please Confirm Large Amount'),
                    body:
                        _t('Are you sure that the customer wants to  pay') +
                        ' ' +
                        this.pos.format_currency(this.currentOrder.get_total_paid()) +
                        ' ' +
                        _t('for an order of') +
                        ' ' +
                        this.pos.format_currency(this.currentOrder.get_total_with_tax()) +
                        ' ' +
                        _t('? Clicking "Confirm" will validate the payment.'),
                    confirm: function() {
                        self.validateOrder(true);
                    },
                });
                return false;
            }

            return true;
        }
        _resetInput() {
            this.isFirstInput = true;
            if (this.selectedPaymentLine) {
                this.inputBuffer = this.pos.format_currency_no_symbol(
                    this.selectedPaymentLine.get_amount()
                );
            } else {
                this.inputBuffer = '';
            }
        }
        _postPushOrderResolve(order, order_server_ids) {
            if (order.is_to_email()) {
                return this._sendReceiptToCustomer(order_server_ids);
            } else {
                return Promise.resolve();
            }
        }
        async _sendReceiptToCustomer(order_server_ids) {
            // TODO: which QWeb will render?
            var order = this.pos.get_order();
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
