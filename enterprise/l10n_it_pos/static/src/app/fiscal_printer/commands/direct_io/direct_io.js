import { Component } from "@odoo/owl";

export class DirectIO extends Component {
    static template = "l10n_it_pos.DirectIO";
    static props = {
        command: { type: String },
        data: { type: String },
        comment: { type: String, optional: true },
    };
    static defaultProps = {
        comment: "",
    };
}
