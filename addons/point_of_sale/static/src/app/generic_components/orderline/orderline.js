/** @odoo-module */

import { Component } from "@odoo/owl";

export class Orderline extends Component {
    static template = "point_of_sale.Orderline";
    static props = {
        class: { type: Object, optional: true },
        line: {
            type: Object,
            shape: {
                productName: String,
                price: String,
                qty: String,
                unit: { type: String, optional: true },
                unitPrice: String,
                discount: { type: String, optional: true },
                combo_parent_id: { type: String, optional: true },
                combo_line_id: { type: String, optional: true },
                oldUnitPrice: { type: String, optional: true },
                customerNote: { type: String, optional: true },
                internalNote: { type: String, optional: true },
                "*": true,
            },
        },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        class: {},
    };
}
