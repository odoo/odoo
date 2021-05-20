/** @odoo-module alias=point_of_sale.ReprintReceiptButton **/

import { useListener } from 'web.custom_hooks';
import PosComponent from 'point_of_sale.PosComponent';

class ReprintReceiptButton extends PosComponent {
    constructor() {
        super(...arguments);
        useListener('click', this._onClick);
    }
    async _onClick() {
        const order = this.props.activeOrder;
        if (!order) return;

        if (this.env.model.proxy && this.env.model.proxy.printer && this.props.orderReceiptRef.el) {
            const receiptHtml = this.props.orderReceiptRef.el.innerHTML;
            const printResult = await this.env.model.proxy.printer.print_receipt(receiptHtml);
            if (!printResult.successful) {
                this.showTempScreen('ReprintReceiptScreen', { order: order });
            }
        } else {
            this.showTempScreen('ReprintReceiptScreen', { order: order });
        }
    }
}
ReprintReceiptButton.template = 'point_of_sale.ReprintReceiptButton';

export default ReprintReceiptButton;
