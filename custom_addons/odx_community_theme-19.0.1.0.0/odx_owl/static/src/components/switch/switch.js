/** @odoo-module **/

import { Component, onWillUpdateProps, useState } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";

export class Switch extends Component {
    static template = "odx_owl.Switch";
    static props = {
        attrs: { type: Object, optional: true },
        ariaLabel: { type: String, optional: true },
        checked: { type: Boolean, optional: true },
        className: { type: String, optional: true },
        defaultChecked: { type: Boolean, optional: true },
        disabled: { type: Boolean, optional: true },
        id: { type: String, optional: true },
        name: { type: String, optional: true },
        onCheckedChange: { type: Function, optional: true },
        required: { type: Boolean, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        attrs: {},
        className: "",
        defaultChecked: false,
        disabled: false,
        required: false,
        value: "on",
    };

    setup() {
        this.state = useState({
            checked: this.props.checked ?? this.props.defaultChecked,
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.checked !== undefined) {
                this.state.checked = nextProps.checked;
            }
        });
    }

    get isChecked() {
        return this.props.checked ?? this.state.checked;
    }

    get classes() {
        return cn("odx-switch", { "odx-switch--checked": this.isChecked }, this.props.className);
    }

    toggle() {
        if (this.props.disabled) {
            return;
        }
        const next = !this.isChecked;
        if (this.props.checked === undefined) {
            this.state.checked = next;
        }
        this.props.onCheckedChange?.(next);
    }
}
