import { Component } from "@odoo/owl";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";

export class CashMoveReceipt extends Component {
    static template = "point_of_sale.CashMoveReceipt";
    static components = { ReceiptHeader };
    static props = {
        reason: String,
        translatedType: String,
        formattedAmount: String,
        headerData: Object,
        date: String,
    };
}
