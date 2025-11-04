import { Component } from "@odoo/owl";

export class CashMoveReceipt extends Component {
    static template = "point_of_sale.CashMoveReceipt";
    static props = {
        reason: String,
        translatedType: String,
        formattedAmount: String,
        date: String,
        order: Object,
    };
}
