/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "./standard_field_props";
import { PercentageEditor, PercentageViewer } from "./percentage";

const { Component, onWillUnmount, onWillUpdateProps, useState } = owl;

export class ProgressBarField extends Component {
    setup() {
        this.eventTimeout = undefined;
        this.notifications = useService("notification");
        this.parse = registry.category("parsers").get("float");
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
    checkFormat(val) {
        if (isNaN(val)) {
            this.notifications.add(this.env._t("Please enter a numerical value"), {
                type: "danger",
            });
            return false;
        }
        return true;
    }
    /**
     * @param {Event} ev
     */
    onChangeCurrentValue(ev) {
        const value = ev.target.value;
        if (this.checkFormat(value)) {
            this.state.currentValue = value;
            this.props.record.update(
                this.props.record.data[this.props.currentValue] !== undefined
                    ? this.props.currentValue
                    : this.props.name,
                this.parse(value)
            );
        }
    }
    /**
     * @param {Event} ev
     */
    onChangeMaxValue(ev) {
        const max_value = ev.target.value;
        if (this.checkFormat(max_value)) {
            this.state.maxValue = max_value;
            this.props.record.update(
                this.props.record.data[this.props.maxValue] !== undefined
                    ? this.props.maxValue
                    : this.props.name,
                this.parse(max_value)
            );
        }
    }
    /**
     * @param {Event} ev
     */
    onKeyDownCurrentValue(ev) {
        this.eventTimeout = browser.setTimeout(() => {
            if (this.checkFormat(ev.target.value)) {
                this.state.currentValue = ev.target.value;
            }
        }, 100);
    }
    /**
     * @param {Event} ev
     */
    onKeyDownMaxValue(ev) {
        this.eventTimeout = browser.setTimeout(() => {
            if (this.checkFormat(ev.target.value)) {
                this.state.maxValue = ev.target.value;
            }
        }, 100);
    }
}
ProgressBarField.components = {
    PercentageEditor,
    PercentageViewer,
};
ProgressBarField.props = {
    ...standardFieldProps,
    currentValue: { type: String, optional: true },
    maxValue: { type: String, optional: true },
    editable: { type: Boolean, optional: true },
    editCurrentValue: { type: Boolean, optional: true },
    editMaxValue: { type: Boolean, optional: true },
};
ProgressBarField.template = "web.ProgressBarField";

ProgressBarField.convertAttrsToProps = function (attrs) {
    return {
        currentValue: attrs.options.current_value,
        maxValue: attrs.options.max_value,
        editable: Boolean(attrs.options.editable),
        editCurrentValue: Boolean(attrs.options.edit_current_value),
        editMaxValue: Boolean(attrs.options.edit_max_value),
    };
};

registry.category("fields").add("progressbar", ProgressBarField);
