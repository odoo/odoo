import { Dialog } from "@web/core/dialog/dialog";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class BillScreen extends Component {
    static template = "pos_restaurant.BillScreen";
    static components = { OrderReceipt, Dialog };
    static props = {
        close: Function,
    };
    setup() {
        this.pos = usePos();
        this.printer = useService("printer");
    }
    async print() {
        await this.pos.printReceipt({
            printBillActionTriggered: true,
        });
    }
}
