import { Component } from "@odoo/owl";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";

export class TipReceipt extends Component {
    static template = "point_of_sale.TipReceipt";
    static components = { ReceiptHeader };
    static props = ["data", "total", "order"];

    get total() {
        return this.props.total;
    }
}
