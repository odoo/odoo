import { Component } from "@odoo/owl";
import { Justification } from "@l10n_it_pos/app/fiscal_printer/commands/types";

export class PrintRecItemAdjustment extends Component {
    static template = "l10n_it_pos.PrintRecItemAdjustment";
    static props = {
        operator: { type: Number, optional: true },
        adjustmentType: { type: Number },
        description: { type: String },
        department: { type: String },
        amount: { type: String },
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
