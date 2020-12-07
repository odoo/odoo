odoo.define('pos_restaurant.TipScreen', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const { parse } = require('web.field_utils');
    const { useState } = owl.hooks;

    class TipScreen extends PosComponent {
        setup() {
            this.state = useState({ inputTipAmount: this.props.activeOrder._extras.TipScreen.inputTipAmount });
            const { withTaxWithDiscount } = this.env.model.getOrderTotals(this.props.activeOrder);
            this.totalAmount = withTaxWithDiscount;
        }
        mounted() {
            setTimeout(() => this._printTipReceipt());
        }
        willUnmount() {
            this.props.activeOrder._extras.TipScreen.inputTipAmount = this.state.inputTipAmount;
        }
        async onValidateTip() {
            const order = this.props.activeOrder;
            if (!order._extras.server_id) {
                return this.env.ui.askUser('ErrorPopup', {
                    title: this.env._t('Unsynced order'),
                    body: this.env._t('This order is not yet synced to server. Make sure it is synced then try again.'),
                });
            }
            const amount = parse.float(this.state.inputTipAmount) || 0;
            await this.env.model.actionHandler({ name: 'actionValidateTip', args: [order, amount, this.nextScreen] });
        }
        get overallAmountStr() {
            const tipAmount = parse.float(this.state.inputTipAmount || '0');
            const original = this.env.model.formatCurrency(this.totalAmount);
            const tip = this.env.model.formatCurrency(tipAmount);
            const overall = this.env.model.formatCurrency(this.totalAmount + tipAmount);
            return `${original} + ${tip} tip = ${overall}`;
        }
        get percentageTips() {
            return [
                { percentage: '15%', amount: 0.15 * this.totalAmount },
                { percentage: '20%', amount: 0.2 * this.totalAmount },
                { percentage: '25%', amount: 0.25 * this.totalAmount },
            ];
        }
        get nextScreen() {
            if (this.env.model.ifaceFloorplan) {
                return 'FloorScreen';
            } else {
                return 'ProductScreen';
            }
        }
        async _printTipReceipt() {
            const activePayment = this.env.model.getActivePayment(this.props.activeOrder);
            const receipts = [activePayment.ticket, activePayment.cashier_receipt];

            for (const data of receipts) {
                const receipt = this.env.qweb.renderToString('pos_restaurant.TipReceipt', {
                    receipt: this.env.model.getOrderInfo(this.props.activeOrder),
                    data: data,
                    total: this.env.model.formatCurrency(this.totalAmount),
                });
                if (this.env.model.proxy.printer) {
                    await this._printIoT(receipt);
                } else {
                    await this._printWeb(receipt);
                }
            }
        }
        async _printIoT(receipt) {
            const printResult = await this.env.model.proxy.printer.print_receipt(receipt);
            if (!printResult.successful) {
                await this.env.ui.askUser('ErrorPopup', {
                    title: printResult.message.title,
                    body: printResult.message.body,
                });
            }
        }
        async _printWeb(receipt) {
            try {
                $(this.el).find('.pos-receipt-container').html(receipt);
                const isPrinted = document.execCommand('print', false, null);
                if (!isPrinted) window.print();
            } catch (err) {
                await this.env.ui.askUser('ErrorPopup', {
                    title: this.env._t('Printing is not supported on some browsers'),
                    body: this.env._t(
                        'Printing is not supported on some browsers due to no default printing protocol ' +
                            'is available. It is possible to print your tickets by making use of an IoT Box.'
                    ),
                });
            }
        }
    }
    TipScreen.template = 'pos_restaurant.TipScreen';

    return TipScreen;
});
