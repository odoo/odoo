import { Component } from "@odoo/owl";
import { Justification } from "@l10n_it_pos/app/fiscal_printer/commands/types";

const PaymentType = {
    CASH: "0",
    CHECK: "1",
    CREDIT: "2",
    TICKET: "3",
    MULTIPLE_TICKETS: "4",
    NOT_PAID: "5",
    PAYMENT_DISCOUNT: "6",
};

export class PrintRecTotal extends Component {
    static template = "l10n_it_pos.PrintRecTotal";
    static props = {
        operator: { type: Number, optional: true },
        description: { type: String },
        payment: { type: String },
        paymentType: {
            type: String,
            validate: (paymentType) => Object.values(PaymentType).includes(paymentType),
        },
        index: { type: Number, optional: true, validate: (index) => index >= 0 },
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
