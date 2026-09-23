import { Component } from "@odoo/owl";

export class TaxTagPopup extends Component {
    static template = "account.tax_tag_popover_template";
    static props = {
        description: { type: String, optional: true },
        invoiceLines: { type: Array, optional: true },
        refundLines: { type: Array, optional: true },
        close: { type: Function, optional: true },
    };
    static defaultProps = {
        invoiceLines: [],
        refundLines: [],
    };

    /**
     * Join the tag names of every repartition line of a given type, suffixing
     * each one with its factor when the line does not take the whole amount.
     */
    formatTags(lines, type) {
        const names = lines
            .filter((line) => line.type === type)
            .flatMap((line) =>
                line.tag_names.map(
                    (name) => name + (line.factor_percent ? ` (${line.factor_percent}%)` : "")
                )
            );
        return names.length ? names.join(", ") : "-";
    }
}
