/** @odoo-module **/

import { Component, onWillUpdateProps } from "@odoo/owl";
import { useForwardRefToParent } from "@web/core/utils/hooks";
import { omit } from "../utils/objects";

export class Input extends Component {
    static template = "web.Input";
    static props = {
        value: String,
        ref: { optional: true },
        "*": true,
    };

    setup() {
        this.ref = useForwardRefToParent("ref");
        this.isEditing = false;
        this.value = this.props.value;
        onWillUpdateProps((np) => {
            if (!this.isEditing && this.value !== np.value) {
                this.value = np.value;
            }
        });
    }

    get htmlAttrs() {
        return omit(this.props, "value", "ref");
    }

    onInput(e) {
        this.isEditing = e.target.value !== this.props.value;
        this.value = e.target.value;
    }

    onChange() {
        this.isEditing = false;
    }
}
