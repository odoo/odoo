import { Component } from "@odoo/owl";
import { Justification } from "@l10n_it_pos/app/fiscal_printer/commands/types";

export class PrintRecItem extends Component {
    static template = "l10n_it_pos.PrintRecItem";
    static props = {
        operator: { type: Number, optional: true },
        description: { type: String },
        quantity: { type: String },
        unitPrice: { type: String },
        department: { type: String },
        justification: {
            type: Number,
            validate: (alignment) => Object.values(Justification).includes(alignment),
            optional: true,
        },
    };
    static defaultProps = {
        operator: 1,
        justification: Justification.FIRST_20,
    };
}
