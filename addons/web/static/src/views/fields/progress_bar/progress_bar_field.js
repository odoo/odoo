import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useNumpadDecimal } from "../numpad_decimal_hook";
import { parseFloat } from "../parsers";
import { standardFieldProps } from "../standard_field_props";

import { Component, useRef, useState } from "@odoo/owl";
const formatters = registry.category("formatters");

export class ProgressBarField extends Component {
    static template = "web.ProgressBarField";
    static props = {
        ...standardFieldProps,
        maxValueField: { type: [String, Number], optional: true },
        currentValueField: { type: String, optional: true },
        isEditable: { type: Boolean, optional: true },
        isCurrentValueEditable: { type: Boolean, optional: true },
        isMaxValueEditable: { type: Boolean, optional: true },
        title: { type: String, optional: true },
        overflowClass: { type: String, optional: true },
    };

    setup() {
        useNumpadDecimal();
        this.root = useRef("numpadDecimal");
        this.maxValueRef = useRef("maxValue");
        this.currentValueRef = useRef("currentValue");

        const { currentValueField, maxValueField, name } = this.props;
        this.currentValueField = currentValueField ? currentValueField : name;
        if (maxValueField) {
            this.maxValueField = maxValueField;
        }

        this.state = useState({
            isEditing: false,
        });
    }

    get isEditable() {
        return this.props.isEditable && !this.props.readonly;
    }
    get isPercentage() {
        return !this.props.maxValueField || !isNaN(this.props.maxValueField);
    }

    get currentValue() {
        return this.props.record.data[this.currentValueField] || 0;
    }

    get maxValue() {
        return this.props.record.data[this.maxValueField] || 100;
    }

    get progressBarColorClass() {
        return this.currentValue > this.maxValue ? this.props.overflowClass : "bg-primary";
    }

    formatCurrentValue(humanReadable = !this.state.isEditing) {
        const formatter = formatters.get(Number.isInteger(this.currentValue) ? "integer" : "float");
        return formatter(this.currentValue, { humanReadable });
    }
    formatMaxValue(humanReadable = !this.state.isEditing) {
        const formatter = formatters.get(Number.isInteger(this.maxValue) ? "integer" : "float");
        return formatter(this.maxValue, { humanReadable });
    }

    onValueChange(value, fieldName) {
        let parsedValue;
        try {
            parsedValue = parseFloat(value);
        } catch {
            this.props.record.setInvalidField(this.props.name);
            return;
        }

        if (this.props.record.fields[fieldName].type === "integer") {
            parsedValue = Math.floor(parsedValue);
        }
        this.props.record.update({ [fieldName]: parsedValue }, { save: this.props.readonly });
    }
    onCurrentValueChange(ev) {
        this.onValueChange(ev.target.value, this.currentValueField);
    }
    onMaxValueChange(ev) {
        this.onValueChange(ev.target.value, this.maxValueField);
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
}

export const progressBarField = {
    component: ProgressBarField,
    displayName: _t("Progress Bar"),
    supportedOptions: [
        {
            label: _t("Can edit value"),
            name: "editable",
            type: "boolean",
        },
        {
            label: _t("Can edit max value"),
            name: "edit_max_value",
            type: "boolean",
        },
        {
            label: _t("Current value field"),
            name: "current_value",
            type: "field",
            availableTypes: ["integer", "float"],
            help: _t(
                "Use to override the display value (e.g. if your progress bar is a computed percentage but you want to display the actual field value instead)."
            ),
        },
        {
            label: _t("Max value field"),
            name: "max_value",
            type: "field",
            availableTypes: ["integer", "float"],
            help: _t(
                "Field that holds the maximum value of the progress bar. If set, will be displayed next to the progress bar (e.g. 10 / 200)."
            ),
        },
        {
            label: _t("Overflow style"),
            name: "overflow_class",
            type: "string",
            availableTypes: ["integer", "float"],
            help: _t(
                "Bootstrap classname to customize the style of the progress bar when the maximum value is exceeded"
            ),
            default: "bg-secondary",
        },
    ],
    supportedTypes: ["integer", "float"],
    extractProps: ({ attrs, options }) => ({
        maxValueField: options.max_value,
        currentValueField: options.current_value,
        isEditable: !options.readonly && options.editable,
        isCurrentValueEditable: options.editable && !options.edit_max_value,
        isMaxValueEditable: options.editable && options.edit_max_value,
        title: attrs.title,
        overflowClass: options.overflow_class || "bg-secondary",
    }),
};

registry.category("fields").add("progressbar", progressBarField);
