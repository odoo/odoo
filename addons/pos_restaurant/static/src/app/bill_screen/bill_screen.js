import { Dialog } from "@web/core/dialog/dialog";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class BillScreen extends Component {
    static template = "pos_restaurant.BillScreen";
    static components = { OrderReceipt, Dialog };
    static props = {
        close: Function,
    };
    setup() {
        this.pos = usePos();
        this.printer = useState(useService("printer"));
    }
    async print() {
<<<<<<< 18.0
        await this.pos.printReceipt({
            printBillActionTriggered: true,
        });
||||||| 5e9fddc41aca643a99e8115e9935c47197985e5b
        await this.pos.printReceipt();
        this.pos.get_order()._printed = false;
=======
        const order = this.pos.get_order();
        await this.pos.printReceipt();
        order._printed = false;
>>>>>>> 7e3b94c94b8c580c3af3d43b0e40cc23b9dd8779
    }
}
