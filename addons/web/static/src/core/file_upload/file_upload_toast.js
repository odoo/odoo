/** @odoo-module */
import { Component } from "@odoo/owl";

export class ProgressBar extends Component {
    static template = "web.ProgressBar";
    static props = {
        progress: { type: Number, optional: true },
        hasError: { type: Boolean, optional: true },
        uploaded: { type: Boolean, optional: true },
        name: String,
        size: { type: String, optional: true },
        errorMessage: { type: String, optional: true },
    };
    static defaultProps = {
        progress: 0,
        hasError: false,
        uploaded: false,
        size: "",
        errorMessage: "",
    };

    get progress() {
        return Math.round(this.props.progress);
    }
}
