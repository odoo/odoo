import { Component } from "@odoo/owl";

export class TipReceipt extends Component {
    static template = "point_of_sale.TipReceipt";
    static props = ["data", "total", "order"];

    get total() {
        return this.props.total;
    }
}
