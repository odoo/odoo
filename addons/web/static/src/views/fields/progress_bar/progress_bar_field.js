/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useNumpadDecimal } from "../numpad_decimal_hook";
import { parseFloat } from "../parsers";
import { standardFieldProps } from "../standard_field_props";

import { Component, onWillUpdateProps, useRef, useState } from "@odoo/owl";
const formatters = registry.category("formatters");
const parsers = registry.category("parsers");

export class ProgressBarField extends Component {
    setup() {
        useNumpadDecimal();
        this.root = useRef("numpadDecimal");
        this.maxValueRef = useRef("maxValue");
        this.currentValueRef = useRef("currentValue");
        this.state = useState({
            currentValue: this.getCurrentValue(this.props),
            maxValue: this.getMaxValue(this.props),
            isEditing: false,
        });
        onWillUpdateProps((nextProps) => {
            Object.assign(this.state, {
                currentValue: this.getCurrentValue(nextProps),
                maxValue: this.getMaxValue(nextProps),
            });
        });
    }

    get isCurrentValueInteger() {
        return this.state.currentValue % 1 === 0;
    }
    get isEditable() {
        return this.props.isEditable && !this.props.readonly;
    }
    get isMaxValueInteger() {
        return this.state.maxValue % 1 === 0;
    }
    get isPercentage() {
        return !this.props.maxValueField || !isNaN(this.props.maxValueField);
    }

    getCurrentValueField(p) {
        return typeof p.currentValueField === "string" ? p.currentValueField : p.name;
    }
    getMaxValueField(p) {
        return typeof p.maxValueField === "string" ? p.maxValueField : p.name;
    }

    getCurrentValue(p) {
        return p.record.data[this.getCurrentValueField(p)] || 0;
    }
    getMaxValue(p) {
        if (p.maxValueField) {
            return p.record.data[p.maxValueField] || 100;
        }
        return 100;
    }

    formatCurrentValue(humanReadable = !this.state.isEditing) {
        const formatter = formatters.get(this.isCurrentValueInteger ? "integer" : "float");
        return formatter(this.state.currentValue, { humanReadable });
    }
    formatMaxValue(humanReadable = !this.state.isEditing) {
        const formatter = formatters.get(this.isMaxValueInteger ? "integer" : "float");
        return formatter(this.state.maxValue, { humanReadable });
    }

    onCurrentValueChange(ev) {
        let parsedValue;
        try {
            parsedValue = parseFloat(ev.target.value);
        } catch {
            this.props.record.setInvalidField(this.props.name);
            return;
        }

        if (this.isCurrentValueInteger) {
            parsedValue = Math.floor(parsedValue);
        }
        this.state.currentValue = parsedValue;
        this.props.record.update({ [this.getCurrentValueField(this.props)]: parsedValue });
        if (this.props.readonly) {
            this.props.record.save();
        }
    }
    onInputBlur() {
        if (
            document.activeElement !== this.maxValueRef.el &&
            document.activeElement !== this.currentValueRef.el
        ) {
            this.state.isEditing = false;
        }
    }
    onInputFocus() {
        this.state.isEditing = true;
    }
    onMaxValueChange(ev) {
        let parsedValue;
        try {
            parsedValue = parseFloat(ev.target.value);
        } catch {
            this.props.record.setInvalidField(this.props.name);
            return;
        }

        if (this.isMaxValueInteger) {
            parsedValue = Math.floor(parsedValue);
        }
        this.state.maxValue = parsedValue;
        this.props.record.update({ [this.getMaxValueField(this.props)]: parsedValue });
        if (this.props.readonly) {
            this.props.record.save();
        }
    }
    onCurrentValueInput(ev) {
        const parser = parsers.get(this.isCurrentValueInteger ? "integer" : "float");
        try {
            this.state.currentValue = parser(ev.target.value);
        } catch {
            // pass
        }
    }
    onMaxValueInput(ev) {
        const parser = parsers.get(this.isMaxValueInteger ? "integer" : "float");
        try {
            this.state.maxValue = parser(ev.target.value);
        } catch {
            // pass
        }
    }
}

ProgressBarField.template = "web.ProgressBarField";
ProgressBarField.props = {
    ...standardFieldProps,
    maxValueField: { type: [String, Number], optional: true },
    currentValueField: { type: String, optional: true },
    isEditable: { type: Boolean, optional: true },
    isCurrentValueEditable: { type: Boolean, optional: true },
    isMaxValueEditable: { type: Boolean, optional: true },
    title: { type: String, optional: true },
};

ProgressBarField.displayName = _lt("Progress Bar");
ProgressBarField.supportedTypes = ["integer", "float"];

ProgressBarField.extractProps = ({ attrs }) => {
    return {
        maxValueField: attrs.options.max_value,
        currentValueField: attrs.options.current_value,
        isEditable: !attrs.options.readonly && attrs.options.editable,
        isCurrentValueEditable: attrs.options.editable && !attrs.options.edit_max_value,
        isMaxValueEditable: attrs.options.editable && attrs.options.edit_max_value,
        title: attrs.title,
    };
};

registry.category("fields").add("progressbar", ProgressBarField);
