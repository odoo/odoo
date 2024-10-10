/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { computeScore } from "./password_policy";
import { Component, xml } from "@odoo/owl";

export class Meter extends Component {
    static template = xml`
        <div class="d-flex align-items-center">
            <meter class="o_password_meter position-relative"
                min="0" low="0.5" high="0.99" max="1" optimum="1"
                t-att-title="title" t-att-value="value"/>
            <span t-out="passwordStrengthParams.text"
                t-attf-class="ms-2 #{passwordStrengthParams.className}"/>
        </div>
    `;
    static props = {
        password: { type: String },
        required: Object,
        recommended: Object,
    };

    get passwordStrengthParams() {
        const strengthRanges = [
            { upperLimit: 0.5, className: "text-danger", text: "Weak" },
            { upperLimit: 0.99, className: "text-warning", text: "Medium" },
            { upperLimit: 1, className: "text-success", text: "Strong" },
        ];

        // Finding the appropriate strength range
        const { className, text } = strengthRanges.find(
            ({ upperLimit }) => this.value <= upperLimit
        );
        return { className, text };
    }

    get title() {
        return _t(
            "Required: %s\n\nHint: to increase password strength, increase length, use multiple words, and use non-letter characters.",
            String(this.props.required) || _t("no requirements")
        );
    }

    get value() {
        return computeScore(this.props.password, this.props.required, this.props.recommended);
    }
}
