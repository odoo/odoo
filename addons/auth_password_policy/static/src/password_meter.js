/** @odoo-module **/

import { sprintf } from "@web/core/utils/strings";
import { computeScore } from "./password_policy";

const { Component } = owl;

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
Meter.template = "auth_password_policy.Meter";
Meter.props = {
    password: { type: String },
    required: Object,
    recommended: Object,
};
