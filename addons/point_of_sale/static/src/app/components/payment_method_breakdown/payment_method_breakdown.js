import { Component, props, types } from "@odoo/owl";
import { AccordionItem } from "@point_of_sale/app/components/accordion_item/accordion_item";

export class PaymentMethodBreakdown extends Component {
    static components = { AccordionItem };
    static template = "point_of_sale.PaymentMethodBreakdown";
    props = props(
        {
            title: types.string(),
            total_amount: types.number(),
            "transactions?": types.array(),
        },
        {
            transactions: [],
        }
    );
}
