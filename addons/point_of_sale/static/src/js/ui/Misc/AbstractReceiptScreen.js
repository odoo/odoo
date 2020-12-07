/** @odoo-module alias=point_of_sale.AbstractReceiptScreen **/

const { useRef } = owl.hooks;
import { nextFrame } from 'point_of_sale.utils';
import PosComponent from 'point_of_sale.PosComponent';

/**
 * This relies on the assumption that there is a reference to
 * `order-receipt` so it is important to declare a `t-ref` to
 * `order-receipt` in the template of the Component that extends
 * this abstract component.
 */
class AbstractReceiptScreen extends PosComponent {
    constructor() {
        super(...arguments);
        this.orderReceipt = useRef('order-receipt');
    }
    async printReceipt() {
        if (this.env.model.proxy.printer) {
            const printResult = await this.env.model.proxy.printer.print_receipt(this.orderReceipt.el.outerHTML);
            if (printResult.successful) {
                return true;
            } else {
                const confirmed = await this.env.ui.askUser('ConfirmPopup', {
                    title: printResult.message.title,
                    body: this.env._t('Do you want to print using the web printer?'),
                });
                if (confirmed) {
                    // We want to call the printWeb when the popup is fully gone
                    // from the screen which happens after the next animation frame.
                    await nextFrame();
                    return this.printWeb();
                }
                return false;
            }
        } else {
            return this.printWeb();
        }
    }
    /**
     * Opens the web printer to print the printable area of the shown screen.
     * https://stackoverflow.com/questions/21285902/printing-a-part-of-webpage-with-javascript
     */
    printWeb() {
        try {
            const isPrinted = document.execCommand('print', false, null);
            if (!isPrinted) window.print();
            return true;
        } catch (err) {
            this.env.ui.askUser('ErrorPopup', {
                title: this.env._t('Printing is not supported on some browsers'),
                body: this.env._t(
                    'Printing is not supported on some browsers due to no default printing protocol ' +
                        'is available. It is possible to print your tickets by making use of an IoT Box.'
                ),
            });
            return false;
        }
    }
}

export default AbstractReceiptScreen;
