/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;
const { onWillUnmount, useState } = owl.hooks;

export class ProgressBarField extends Component {
    setup() {
        this.eventTimeout = undefined;
        this.notifications = useService("notification");
        this.state = useState({
            currentValue: this.currentValue,
            maxValue: this.maxValue,
        });
        onWillUnmount(() => {
            browser.clearTimeout(this.actionTimeoutId);
            browser.clearTimeout(this.resetTimeoutId);
        });
    }
    get currentValue() {
        let value = this.props.record.data[this.props.name] || 0;
        if (this.props.options.current_value) {
            value = this.props.record.data[this.props.options.current_value];
        }
        return value;
    }
    get maxValue() {
        let value = 100;
        if (this.props.options.max_value) {
            value = this.props.record.data[this.props.options.max_value];
        }
        return value;
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
            this.props.update(Number(value) || false, { name: this.props.options.current_value });
        }
    }
    /**
     * @param {Event} ev
     */
    onChangeMaxValue(ev) {
        const max_value = ev.target.value;
        if (this.checkFormat(max_value)) {
            this.state.maxValue = max_value;
            this.props.update(Number(max_value) || false, { name: this.props.options.max_value });
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
ProgressBarField.props = standardFieldProps;
ProgressBarField.template = "web.ProgressBarField";

registry.category("fields").add("progressbar", ProgressBarField);
