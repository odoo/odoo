import { Component, t, useProps } from "@odoo/owl";

export class TaxTagPopup extends Component {
    static template = "account.tax_tag_popover_template";
    props = useProps({
        description: t.string().optional(),
        invoiceLines: t.array().optional(),
        refundLines: t.array().optional(),
        close: t.function().optional(),
    });
}
