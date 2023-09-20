/** @odoo-module */

import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component } from "@odoo/owl";
import { renderToElement } from "@web/core/utils/render";
import { useService } from "@web/core/utils/hooks";
import { useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";

export class ReprintReceiptButton extends Component {
    static template = "point_of_sale.ReprintReceiptButton";

    setup() {
        this.pos = usePos();
        this.hardwareProxy = useService("hardware_proxy");
        this.click = useAsyncLockedMethod(this.click);
    }

    async click() {
        if (!this.props.order) {
            return;
        }
        if (this.hardwareProxy.printer) {
            const orderReceipt = renderToElement("point_of_sale.OrderReceipt", {
                receiptData: {
                    ...this.props.order.getOrderReceiptEnv(),
                },
                pos: this.pos,
                env: this.env,
            });

            // Need to await to have the result in case of automatic skip screen.
            await this.hardwareProxy.printer.printReceipt(orderReceipt);
        } else {
            this.pos.showScreen("ReprintReceiptScreen", { order: this.props.order });
        }
    }
}
