/** @odoo-module **/

import { sprintf } from "@web/core/utils/strings";
import { computeScore, Policy } from "./password_policy";

const { Component, xml } = owl;

export class Meter extends Component {
    get title() {
        return sprintf(
            this.env._t(
                "Required: %s\n\nHint: to increase password strength, increase length, use multiple words, and use non-letter characters."
            ),
            String(this.props.required) || this.env._t("no requirements")
        );
    }

    get value() {
        return computeScore(this.props.password, this.props.required, this.props.recommended);
    }
}
Meter.template = xml`
<meter class="o_password_meter"
       min="0" low="0.5" high="0.99" max="1" optimum="1"
       t-att-title="title" t-att-value="value"/>
`;
Meter.props = {
    password: { type: String },
    required: Policy,
    recommended: Policy,
};
