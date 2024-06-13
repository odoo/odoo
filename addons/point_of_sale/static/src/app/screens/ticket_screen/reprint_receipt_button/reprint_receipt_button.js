import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { useAsyncLockedMethod } from "@point_of_sale/app/utils/hooks";

export class ReprintReceiptButton extends Component {
    static template = "point_of_sale.ReprintReceiptButton";
    static props = {
        order: Object,
    };

    setup() {
        this.pos = usePos();
        this.printer = useService("printer");
        this.click = useAsyncLockedMethod(this.click);
    }

    async click() {
        if (!this.props.order) {
            return;
        }
        // Need to await to have the result in case of automatic skip screen.
        (await this.printer.print(OrderReceipt, {
            data: this.pos.orderExportForPrinting(this.props.order),
            formatCurrency: this.env.utils.formatCurrency,
        })) || this.pos.showScreen("ReprintReceiptScreen", { order: this.props.order });
    }
}
