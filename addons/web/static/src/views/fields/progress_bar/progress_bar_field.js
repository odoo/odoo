import { _t } from "@web/core/l10n/translation";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { useNumpadDecimal } from "../numpad_decimal_hook";
import { parseFloat } from "../parsers";
import { useInputField } from "@web/views/fields/input_field_hook";
import { standardFieldProps } from "../standard_field_props";

import { Component, useEffect, useRef, useState } from "@odoo/owl";
const formatters = registry.category("formatters");

export class ProgressBarField extends Component {
    static template = "web.ProgressBarField";
    static props = {
        ...standardFieldProps,
        maxValueField: { type: [String, Number], optional: true },
        isEditable: { type: Boolean, optional: true },
        title: { type: String, optional: true },
        decorations: { type: Object, optional: true },
    };
    static defaultProps = {
        decorations: {},
    };

    setup() {
        useNumpadDecimal();
        this.root = useRef("numpadDecimal");

        this.currentValueRef = useInputField({
            getValue: () => this.formatCurrentValue(),
            parse: (v) => this.parseCurrentValue(v),
            refName: "currentValue",
            fieldName: this.props.name,
            shouldSave: () => this.props.readonly,
        });

        this.state = useState({
            isEditing: false,
        });

        useEffect(
            () => {
                this.resizeInput();
            },
            () => [this.currentValue, this.state.isEditing]
        );
    }

    resizeInput() {
        const input = this.currentValueRef.el;
        if (input) {
            const displayValue = this.state.isEditing ? input.value : this.formatCurrentValue();
            const charCount = Math.max(3, (displayValue?.toString().length || 0) + 1);
            input.style.width = `${charCount}ch`;
        }
    }

    get isEditable() {
        return this.props.isEditable;
    }
    get isPercentage() {
        return !this.props.maxValueField || !isNaN(this.props.maxValueField);
    }

    get currentValue() {
        return this.props.record.data[this.props.name] || 0;
    }

    get maxValue() {
        return this.props.record.data[this.props.maxValueField] || 100;
    }

    get progressBarColorClass() {
        if (this.props.decorations) {
            const evalContext = this.props.record.evalContextWithVirtualIds;
            for (const decorationName in this.props.decorations) {
                if (evaluateBooleanExpr(this.props.decorations[decorationName], evalContext)) {
                    return `progress-bar bg-${decorationName}`;
                }
            }
        }
        return "progress-bar";
    }

    formatCurrentValue(humanReadable = !this.state.isEditing) {
        const formatter = formatters.get(this.props.record.fields[this.props.name].type);
        return formatter(this.currentValue, { humanReadable });
    }

    formatMaxValue(humanReadable = !this.state.isEditing) {
        const formatter = formatters.get(this.props.record.fields[this.props.maxValueField]?.type ?? "integer");
        return formatter(this.maxValue, { humanReadable });
    }

    parseCurrentValue(value) {
        let parsedValue = parseFloat(value);
        if (this.props.record.fields[this.props.name].type === "integer") {
            parsedValue = Math.floor(parsedValue);
        }
        return parsedValue;
    }

    onInputBlur() {
        if (document.activeElement !== this.currentValueRef.el) {
            this.state.isEditing = false;
        }
    }
    onInputFocus() {
        this.state.isEditing = true;
        this.resizeInput();
    }

    onInputChange() {
        this.resizeInput();
    }

    onProgressClick() {
        if (this.isEditable) {
            const input = this.root.el?.querySelector(".o_progressbar_value input");
            if (input) {
                input.focus();
            }
        }
    }
}

export const progressBarField = {
    component: ProgressBarField,
    displayName: _t("Progress Bar"),
    supportedOptions: [
        {
            label: _t("Max value field"),
            name: "max_value",
            type: "field",
            availableTypes: ["integer", "float"],
            help: _t(
                "Field that holds the maximum value of the progress bar. If set, will be displayed next to the progress bar (e.g. 10 / 200)."
            ),
        },
    ],
    supportedTypes: ["integer", "float"],
    extractProps: (fieldInfo, dynamicInfo) => ({
        maxValueField: fieldInfo.options.max_value,
        isEditable: fieldInfo.readonly !== null && !dynamicInfo.readonly,
        title: fieldInfo.attrs.title,
        decorations: fieldInfo.decorations,
    }),
};

registry.category("fields").add("progressbar", progressBarField);
