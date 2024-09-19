import { Component } from "@odoo/owl";
import { AccordionItem } from "@point_of_sale/app/generic_components/accordion_item/accordion_item";

export class PaymentMethodBreakdown extends Component {
    static components = { AccordionItem };
    static template = "point_of_sale.PaymentMethodBreakdown";

    static props = {
        title: String,
        total_amount: Number,
        transactions: { type: Array, optional: true },
    };

    static defaultProps = {
        transactions: [],
    };
}
