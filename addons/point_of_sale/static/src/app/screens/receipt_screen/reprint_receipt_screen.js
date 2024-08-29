import { usePos } from "@point_of_sale/app/store/pos_hook";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ReprintReceiptScreen extends Component {
    static template = "point_of_sale.ReprintReceiptScreen";
    static components = { OrderReceipt };
    static storeOnOrder = false;
    static props = ["order"];
    setup() {
        super.setup();
        this.pos = usePos();
        this.printer = useService("printer");
    }

    confirm() {
        this.pos.showScreen("TicketScreen");
    }

    tryReprint() {
        this.printer.print(
            OrderReceipt,
            {
                data: this.pos.orderExportForPrinting(this.props.order),
                formatCurrency: this.env.utils.formatCurrency,
            },
            { webPrintFallback: true }
        );
    }
}

registry.category("pos_screens").add("ReprintReceiptScreen", ReprintReceiptScreen);
