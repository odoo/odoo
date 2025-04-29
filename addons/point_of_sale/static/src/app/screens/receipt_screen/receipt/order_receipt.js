/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { omit } from "@web/core/utils/objects";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class OrderReceipt extends Component {
    static template = "point_of_sale.OrderReceipt";
    static components = {
        Orderline,
        OrderWidget,
        ReceiptHeader,
    };
    static props = {
        data: Object,
        formatCurrency: Function,
    };
    omit(...args) {
        return omit(...args);
    };
    setup() {
        super.setup();
        /* usePos will error in self order because the asset bundle not loading all necessary stuff */
        try {
           this.pos = usePos();
        } catch {
           this.pos = null;
        }
    }
}
