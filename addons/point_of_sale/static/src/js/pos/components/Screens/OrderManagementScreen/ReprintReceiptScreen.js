/** @odoo-module alias=point_of_sale.ReprintReceiptScreen **/

import AbstractReceiptScreen from 'point_of_sale.AbstractReceiptScreen';
import OrderReceipt from 'point_of_sale.OrderReceipt';

class ReprintReceiptScreen extends AbstractReceiptScreen {
    confirm() {
        this.props.resolve();
        this.trigger('close-temp-screen');
    }
    tryReprint() {
        this.printReceipt();
    }
}
ReprintReceiptScreen.template = 'point_of_sale.ReprintReceiptScreen';
ReprintReceiptScreen.components = { OrderReceipt };

export default ReprintReceiptScreen;
