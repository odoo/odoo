<<<<<<< 3ff8b8d99d2c70933add63e610f7b732f12334fa
import { Component, t, useProps } from "@odoo/owl";
||||||| 32c8687979f6144fd4ec6e0bb8d4beeb7c3760c5
import { Component } from "@odoo/owl";
=======
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
>>>>>>> 8297b067c58f2c2d05e2c45608630f86626e6505

export class TaxTagPopup extends Component {
    static template = "account.tax_tag_popover_template";
<<<<<<< 3ff8b8d99d2c70933add63e610f7b732f12334fa
    props = useProps({
        description: t.string().optional(),
        invoiceLines: t.array().optional(),
        refundLines: t.array().optional(),
        close: t.function().optional(),
    });
||||||| 32c8687979f6144fd4ec6e0bb8d4beeb7c3760c5
    static props = {
        description: { type: String, optional: true },
        invoiceLines: { type: Array, optional: true },
        refundLines: { type: Array, optional: true },
        close: { type: Function, optional: true },
    };
=======
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
>>>>>>> 8297b067c58f2c2d05e2c45608630f86626e6505
}
