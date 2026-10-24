import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

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
     * Returns an empty string when the type carries no tag, so that the rows
     * and columns without any are left out.
     */
    formatTags(lines, type) {
        return lines
            .filter((line) => line.type === type)
            .flatMap((line) =>
                line.tag_names.map(
                    (name) => name + (line.factor_percent ? ` (${line.factor_percent}%)` : "")
                )
            )
            .join(", ");
    }

    /**
     * The rows of the table, leaving out the ones without any tag.
     */
    get rows() {
        return [
            { label: _t("Invoice"), lines: this.props.invoiceLines },
            { label: _t("Credit Note"), lines: this.props.refundLines },
        ]
            .map(({ label, lines }) => ({
                label,
                base: this.formatTags(lines, "base"),
                tax: this.formatTags(lines, "tax"),
            }))
            .filter((row) => row.base || row.tax);
    }

    /**
     * Only the types carrying a tag in some row get a column, so that a lone
     * one is not pushed aside by an empty column.
     */
    getTypes(rows) {
        return ["base", "tax"].filter((type) => rows.some((row) => row[type]));
    }
}
