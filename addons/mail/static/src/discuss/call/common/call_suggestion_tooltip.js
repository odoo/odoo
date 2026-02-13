import { Component } from "@odoo/owl";

export class CallSuggestionTooltip extends Component {
    static template = "mail.CallSuggestionTooltip";
    static props = {
        text: String,
        onDismiss: Function,
        close: Function,
    };
}
