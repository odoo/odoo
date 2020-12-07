/** @odoo-module alias=point_of_sale.ReceiptScreen **/

import { is_email } from 'web.utils';
import OrderReceipt from 'point_of_sale.OrderReceipt';
import AbstractReceiptScreen from 'point_of_sale.AbstractReceiptScreen';

class ReceiptScreen extends AbstractReceiptScreen {
    constructor() {
        super(...arguments);
        this.orderUiState = this.props.activeOrder._extras.ReceiptScreen;
        if (!this.orderUiState.inputEmail) {
            const client = this.env.model.getRecord('res.partner', this.props.activeOrder.partner_id);
            this.orderUiState.inputEmail = client ? client.email : '';
        }
    }
    mounted() {
        // Here, we send a task to the event loop that handles
        // the printing of the receipt when the component is mounted.
        // We are doing this because we want the receipt screen to be
        // displayed regardless of what happen to the _handleAutoPrint
        // call.
        setTimeout(() => this._handleAutoPrint(), 0);
    }
    onEmailInput(event) {
        this.orderUiState.inputEmail = event.target.value;
        // NOTE: This is necessary to correctly show the send button, however, I'm not
        // sure about the implication of this since it seems to be inefficient.
        // However, this is also what happens when using `useState` -- `render` method
        // is also triggered whenever a value in the state is changed.
        this.render();
    }
    onSendEmail() {
        this.env.model.actionHandler({
            name: 'actionSendReceipt',
            args: [this.props.activeOrder, this.orderReceipt.el],
        });
    }
    async onPrintReceipt() {
        const printed = await this.printReceipt();
        if (printed) {
            this.props.activeOrder._extras.printed++;
        }
    }
    /**
     * This function is called outside the rendering call stack. This way,
     * we don't block the displaying of ReceiptScreen when it is mounted; additionally,
     * any error that can happen during the printing does not affect the rendering.
     */
    async _handleAutoPrint() {
        if (this._shouldAutoPrint()) {
            await this.onPrintReceipt();
            if (this.props.activeOrder._extras.printed && this._shouldCloseImmediately()) {
                await this.onOrderDone();
            }
        }
    }
    _shouldAutoPrint() {
        return this.env.model.config.iface_print_auto && !this.props.activeOrder._extras.printed;
    }
    _shouldCloseImmediately() {
        return this.env.model.proxy.printer && this.env.model.config.iface_print_skip_screen;
    }
    async onOrderDone() {
        await this.env.model.actionHandler({
            name: 'actionOrderDone',
            args: [this.props.activeOrder, this.nextScreen],
        });
    }
    get nextScreen() {
        return 'ProductScreen';
    }
    get highlightSendButton() {
        return is_email(this.orderUiState.inputEmail);
    }
    get orderAmountPlusTip() {
        const order = this.props.activeOrder;
        const { withTaxWithDiscount: orderTotal } = this.env.model.getOrderTotals(order);
        const tip_product_id = this.env.model.config.tip_product_id;
        const tipLine = this.env.model.getOrderlines(order).find((line) => line.product_id === tip_product_id);
        const { priceWithTax: tipAmount } = tipLine ? this.env.model.getOrderlinePrices(tipLine) : { priceWithTax: 0 };
        if (this.env.model.floatCompare(tipAmount, 0) === 0) {
            // meaning, tipAmount is zero
            return this.env.model.formatCurrency(orderTotal);
        } else {
            const orderTotalStr = this.env.model.formatCurrency(orderTotal - tipAmount);
            const tipAmountStr = this.env.model.formatCurrency(tipAmount);
            return `${orderTotalStr} + ${tipAmountStr} tip`;
        }
    }
}
ReceiptScreen.template = 'point_of_sale.ReceiptScreen';
ReceiptScreen.components = { OrderReceipt };

export default ReceiptScreen;
