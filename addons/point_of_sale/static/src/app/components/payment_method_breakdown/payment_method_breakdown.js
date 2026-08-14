import { Component, useProps, t } from "@odoo/owl";
import { AccordionItem } from "@point_of_sale/app/components/accordion_item/accordion_item";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class PaymentMethodBreakdown extends Component {
    static components = { AccordionItem, PaymentMethodBreakdown };
    static template = "point_of_sale.PaymentMethodBreakdown";

    props = useProps({
        title: t.string(),
        total_amount: t.number(),
        transactions: t
            .array(
                t.object({
                    id: t.number(),
                    name: t.string(),
                    amount: t.number(),
                    subTransactions: t.array().optional(),
                })
            )
            .optional([]),
    });

    setup() {
        this.pos = usePos();
    }
}
