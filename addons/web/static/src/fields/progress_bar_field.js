/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "./standard_field_props";
import { parseFloat } from "./parsers";

const { Component, onWillUnmount, onWillUpdateProps, useState } = owl;

export class ProgressBarField extends Component {
    setup() {
        this.eventTimeout = undefined;
        this.notifications = useService("notification");
        this.state = useState({
            currentValue: this.getFieldValue("currentValue"),
            maxValue: this.getFieldValue("maxValue"),
        });
        onWillUnmount(() => {
            browser.clearTimeout(this.eventTimeout);
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.readonly) {
                Object.assign(this.state, {
                    currentValue: this.getFieldValue("currentValue"),
                    maxValue: this.getFieldValue("maxValue"),
                });
            }
        });
    }
    getFieldValue(val) {
        if (this.props[val]) {
            if (isNaN(this.props[val])) {
                return (
                    (this.props.record.data[this.props[val]] !== undefined &&
                        this.props.record.data[this.props[val]]) ||
                    0
                );
            } else {
                return this.props[val];
            }
        }
        return val === "max_value" ? 100 : this.props.record.data[this.props.name] || 0;
    }

    /**
     * @param {String} value
     * @param {String} part
     */
    onChangeValue(value, part) {
        try {
            this.state[part] = value;
            this.props.record.update(
                this.props.record.data[this.props[part]] !== undefined
                    ? this.props[part]
                    : this.props.name,
                this.props.maxValue ? parseFloat(value) : Math.floor(parseFloat(value))
            );
        } catch {
            //this.props.record.setInvalidField(this.props.name); WOWL FIXME It works but stays invalid
            this.notifications.add(this.env._t("Please enter a numerical value"), {
                type: "danger",
            });
        }
    }

    /**
     * @param {Event} ev
     * @param {String} part
     */
    onKeyDownValue(ev, part) {
        this.eventTimeout = browser.setTimeout(() => {
            try {
                this.state[part] = parseFloat(ev.target.value);
            } catch {}
        }, 100);
    }
}

ProgressBarField.props = {
    ...standardFieldProps,
    currentValue: { type: String, optional: true },
    maxValue: { type: String, optional: true },
    editable: { type: Boolean, optional: true },
    editCurrentValue: { type: Boolean, optional: true },
    editMaxValue: { type: Boolean, optional: true },
};
ProgressBarField.template = "web.ProgressBarField";
ProgressBarField.convertAttrsToProps = (attrs) => {
    return {
        currentValue: attrs.options.current_value,
        maxValue: attrs.options.max_value,
        editable: Boolean(attrs.options.editable),
        editCurrentValue: Boolean(attrs.options.edit_current_value),
        editMaxValue: Boolean(attrs.options.edit_max_value),
    };
};

registry.category("fields").add("progressbar", ProgressBarField);
