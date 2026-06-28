import { Component, props, t } from "@odoo/owl";
import { AccordionItem } from "@point_of_sale/app/components/accordion_item/accordion_item";

export class PaymentMethodBreakdown extends Component {
    static components = { AccordionItem };
    static template = "point_of_sale.PaymentMethodBreakdown";

    props = props({
        title: t.string(),
        total_amount: t.number(),
        transactions: t.array().optional([]),
    });
}
