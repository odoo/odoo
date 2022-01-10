/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "./standard_field_props";
import { PercentageEditor, PercentageViewer } from "./percentage";

const { Component } = owl;
const { onWillUnmount, onWillUpdateProps, useState } = owl.hooks;

export class ProgressBarField extends Component {
    setup() {
        this.eventTimeout = undefined;
        this.notifications = useService("notification");
        this.state = useState({
            currentValue: this.getFieldValue("current_value"),
            maxValue: this.getFieldValue("max_value"),
        });
        onWillUnmount(() => {
            browser.clearTimeout(this.eventTimeout);
        });
        onWillUpdateProps((nextProps) => {
            if (nextProps.readonly) {
                Object.assign(this.state, {
                    currentValue: this.getFieldValue("current_value"),
                    maxValue: this.getFieldValue("max_value"),
                });
            }
        });
    }
    getFieldValue(val) {
        if (this.props.options[val]) {
            if (isNaN(this.props.options[val])) {
                return (
                    (this.props.record.data[this.props.options[val]] !== undefined &&
                        this.props.record.data[this.props.options[val]]) ||
                    0
                );
            } else {
                return this.props.options[val];
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
                this.props.record.data[this.props.options.current_value] !== undefined
                    ? this.props.options.current_value
                    : this.props.name,
                Number(value) || false
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
                this.props.record.data[this.props.options.max_value] !== undefined
                    ? this.props.options.max_value
                    : this.props.name,
                Number(max_value) || false
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
ProgressBarField.props = standardFieldProps;
ProgressBarField.template = "web.ProgressBarField";

registry.category("fields").add("progressbar", ProgressBarField);
