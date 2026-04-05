/** @odoo-module **/

import { Component, onWillUpdateProps, useState } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";

function isCheckboxState(value) {
    return typeof value === "boolean" || value === "indeterminate";
}

export class Checkbox extends Component {
    static template = "odx_owl.Checkbox";
    static props = {
        attrs: { type: Object, optional: true },
        ariaLabel: { type: String, optional: true },
        checked: { optional: true, validate: isCheckboxState },
        className: { type: String, optional: true },
        defaultChecked: { optional: true, validate: isCheckboxState },
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

    get checkedState() {
        return this.props.checked ?? this.state.checked;
    }

    get isIndeterminate() {
        return this.checkedState === "indeterminate";
    }

    get isChecked() {
        return this.checkedState === true;
    }

    get ariaChecked() {
        return this.isIndeterminate ? "mixed" : this.isChecked ? "true" : "false";
    }

    get dataState() {
        return this.isIndeterminate ? "indeterminate" : this.isChecked ? "checked" : "unchecked";
    }

    get shouldSubmit() {
        return this.isChecked;
    }

    get classes() {
        return cn(
            "odx-checkbox",
            {
                "odx-checkbox--checked": this.isChecked,
                "odx-checkbox--indeterminate": this.isIndeterminate,
            },
            this.props.className
        );
    }

    toggle() {
        if (this.props.disabled) {
            return;
        }
        const next = this.isChecked ? false : true;
        if (this.props.checked === undefined) {
            this.state.checked = next;
        }
        this.props.onCheckedChange?.(next);
    }
}
