import { Component } from "@odoo/owl";

export class DisplayText extends Component {
    static template = "l10n_it_pos.DisplayText";
    static props = {
        operator: { type: Number, optional: true },
        message: { type: String },
    };
    static defaultProps = {
        operator: 1,
    };
}
