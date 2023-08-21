/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { Component, useRef } from "@odoo/owl";

/**
 * This relies on the assumption that there is a reference to
 * `order-receipt` so it is important to declare a `t-ref` to
 * `order-receipt` in the template of the Component that extends
 * this abstract component.
 */
export class AbstractReceiptScreen extends Component {
    setup() {
        this.orderReceipt = useRef("order-receipt");
        this.popup = useService("popup");
        this.hardwareProxy = useService("hardware_proxy");
    }
    async _printReceipt() {
        if (this.hardwareProxy.printer) {
            const printResult = await this.hardwareProxy.printer.printReceipt(
                this.orderReceipt.el.firstChild.firstChild
            );
            if (printResult.successful) {
                return true;
            } else {
                await this.popup.add(ErrorPopup, {
                    title: printResult.message.title,
                    body: printResult.message.body,
                });
                const { confirmed } = await this.popup.add(ConfirmPopup, {
                    title: printResult.message.title,
                    body: _t("Do you want to print using the web printer?"),
                });
                if (confirmed) {
                    // We want to call the _printWeb when the popup is fully gone
                    // from the screen which happens after the next animation frame.
                    await new Promise(requestAnimationFrame);
                    return await this._printWeb();
                }
                return false;
            }
        } else {
            return await this._printWeb();
        }
    }
    async _printWeb() {
        try {
            window.print();
            return true;
        } catch {
            await this.popup.add(ErrorPopup, {
                title: _t("Printing is not supported on some browsers"),
                body: _t(
                    "Printing is not supported on some browsers due to no default printing protocol " +
                        "is available. It is possible to print your tickets by making use of an IoT Box."
                ),
            });
            return false;
        }
    }
}
