// @ts-check
/** @odoo-module native */

import { Component, useRef, useState } from "@odoo/owl";
import { getFieldCodec } from "@web/core/field_codec";
import { parseFloat, parseInteger } from "@web/core/parsers";
import { _t } from "@web/core/translation";
import { registerField } from "@web/fields/_registry";
import { archAttribute } from "@web/fields/field_options";
import { isFalseEmpty } from "@web/fields/field_utils";
import { useInputField } from "@web/fields/input_field_hook";
import { useNumpadDecimal } from "@web/fields/numpad_decimal_hook";
import { standardFieldProps } from "@web/fields/standard_field_props";

/**
 * @typedef {import("@web/fields/standard_field_props").StandardFieldProps & {
 * maxValueField?: string | number;
 * currentValueField?: string;
 * isEditable?: boolean;
 * isCurrentValueEditable?: boolean;
 * isMaxValueEditable?: boolean;
 * required?: boolean;
 * title?: string;
 * overflowClass?: string;
 * }} ProgressBarFieldProps
 */

/**
 * @param {string | number | undefined} value
 * @returns {number | undefined}
 */
function toFiniteNumber(value) {
    if (value === undefined || value === null || value === "") {
        return undefined;
    }
    const parsed = typeof value === "number" ? value : Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
}

/**
 * @param {string} fieldName
 * @param {Record<string, any>} options
 * @returns {string[]}
 */
function editedFieldNames(fieldName, options) {
    const names = [options.current_value || fieldName];
    if (options.max_value && toFiniteNumber(options.max_value) === undefined) {
        names.push(String(options.max_value));
    }
    return names;
}

/** @extends {Component<ProgressBarFieldProps>} */
export class ProgressBarField extends Component {
    static template = "web.ProgressBarField";
    static props = {
        ...standardFieldProps,
        maxValueField: { type: [String, Number], optional: true },
        currentValueField: { type: String, optional: true },
        isEditable: { type: Boolean, optional: true },
        isCurrentValueEditable: { type: Boolean, optional: true },
        isMaxValueEditable: { type: Boolean, optional: true },
        required: { type: Boolean, optional: true },
        title: { type: String, optional: true },
        overflowClass: { type: String, optional: true },
    };

    setup() {
        useNumpadDecimal();
        this.root = useRef("numpadDecimal");

        const {
            currentValueField,
            maxValueField: maxValueFieldProp,
            name,
        } = this.props;
        this.currentValueField = currentValueField ? currentValueField : name;

        this.maxValueLiteral = toFiniteNumber(maxValueFieldProp);
        this.maxValueFieldName =
            this.maxValueLiteral === undefined && maxValueFieldProp
                ? String(maxValueFieldProp)
                : undefined;

        this.currentValueRef = useInputField({
            getValue: () => this.formatValue(this.currentValueField, this.currentValue),
            parse: (v) => this.parseValue(this.currentValueField, v),
            refName: "currentValue",
            fieldName: this.currentValueField,
            shouldSave: () => this.shouldSaveImmediately,
        });
        this.maxValueRef = useInputField({
            getValue: () => this.formatValue(this.maxValueFieldName, this.maxValue),
            parse: (v) => this.parseValue(this.maxValueFieldName, v),
            refName: "maxValue",
            fieldName: this.maxValueFieldName,
            shouldSave: () => this.shouldSaveImmediately,
        });

        this.state = useState({
            isEditing: false,
        });
    }

    /** @returns {boolean} */
    get shouldSaveImmediately() {
        return !this.props.record.isInEdition;
    }

    /** @returns {boolean} */
    get isEditable() {
        return this.props.isEditable && !this.props.readonly;
    }

    /** @returns {boolean} */
    get isPercentage() {
        return this.maxValueLiteral === undefined && !this.maxValueFieldName;
    }

    /** @returns {boolean} */
    get canEditMaxValue() {
        return Boolean(
            this.isEditable && this.props.isMaxValueEditable && this.maxValueFieldName,
        );
    }

    /** @returns {number} */
    get currentValue() {
        return (
            /** @type {Record<string, any>} */ (this.props.record.data)[
                this.currentValueField
            ] || 0
        );
    }

    /** @returns {number} */
    get maxValue() {
        if (this.maxValueLiteral !== undefined) {
            return this.maxValueLiteral;
        }
        const value = /** @type {Record<string, any>} */ (this.props.record.data)[
            this.maxValueFieldName
        ];
        return value === false ? 0 : (value ?? 100);
    }

    /** @returns {string} */
    get progressBarStyle() {
        const max = this.maxValue;
        const ratio = max > 0 ? (100 * this.currentValue) / max : 0;
        return `width: min(${Math.max(ratio, 0)}%, 100%)`;
    }

    /** @returns {string} */
    get progressBarColorClass() {
        return this.currentValue > this.maxValue
            ? this.props.overflowClass
            : "bg-primary";
    }

    /**
     * @param {string} fieldName
     * @param {number} value
     * @param {boolean} [humanReadable]
     * @returns {string}
     */
    formatValue(fieldName, value, humanReadable = !this.state.isEditing) {
        const type = this.props.record.fields[fieldName]?.type ?? "integer";
        return getFieldCodec(type).format(value, { humanReadable });
    }

    /**
     * @param {boolean} humanReadable
     * @returns {string}
     */
    formatCurrentValue(humanReadable) {
        return this.formatValue(
            this.currentValueField,
            this.currentValue,
            humanReadable,
        );
    }

    /**
     * @param {boolean} humanReadable
     * @returns {string}
     */
    formatMaxValue(humanReadable) {
        return this.formatValue(this.maxValueFieldName, this.maxValue, humanReadable);
    }

    /**
     * @param {string} fieldName
     * @param {string} value
     * @returns {number}
     */
    parseValue(fieldName, value) {
        return this.props.record.fields[fieldName]?.type === "integer"
            ? parseInteger(value, { allowOperation: true })
            : parseFloat(value, { allowOperation: true });
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

/** @type {import("registries").FieldsRegistryItemShape} */
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
                "Use to override the display value (e.g. if your progress bar is a computed percentage but you want to display the actual field value instead).",
            ),
        },
        {
            label: _t("Max value field"),
            name: "max_value",
            type: "field",
            availableTypes: ["integer", "float"],
            help: _t(
                "Field that holds the maximum value of the progress bar. If set, will be displayed next to the progress bar (e.g. 10 / 200).",
            ),
        },
        {
            label: _t("Overflow style"),
            name: "overflow_class",
            type: "string",
            availableTypes: ["integer", "float"],
            help: _t(
                "Bootstrap classname to customize the style of the progress bar when the maximum value is exceeded",
            ),
            default: "bg-secondary",
        },
        {
            label: _t("Force read-only"),
            name: "force_readonly",
            type: "boolean",
            help: _t(
                "Force the bar non-editable even when 'Can edit value' is set -- used to keep a card's bar inert in kanban.",
            ),
        },
    ],
    supportedAttributes: [
        archAttribute("title", _t("Title"), {
            help: _t("Label drawn beside the bar."),
        }),
    ],
    isEmpty: isFalseEmpty,
    supportedTypes: ["integer", "float"],
    isValid: (
        /** @type {any} */ record,
        /** @type {string} */ fieldName,
        /** @type {any} */ fieldInfo,
    ) =>
        !editedFieldNames(fieldName, fieldInfo.options || {}).some((name) =>
            record.isFieldInvalid(name),
        ),
    fieldDependencies: ({ options }) => {
        const editable = Boolean(options.editable) && !options.force_readonly;
        const deps = [];
        if (options.current_value) {
            deps.push({
                name: options.current_value,
                optional: true,
                readonly: !(editable && !options.edit_max_value),
            });
        }
        if (options.max_value && toFiniteNumber(options.max_value) === undefined) {
            deps.push({
                name: String(options.max_value),
                optional: true,
                readonly: !(editable && options.edit_max_value),
            });
        }
        return deps;
    },
    extractProps: ({ attrs, options }, dynamicInfo) => ({
        maxValueField: options.max_value,
        currentValueField: options.current_value,
        isEditable: !options.force_readonly && options.editable,
        isCurrentValueEditable: options.editable && !options.edit_max_value,
        isMaxValueEditable: options.editable && options.edit_max_value,
        required: dynamicInfo.required,
        title: attrs.title,
        overflowClass: options.overflow_class || "bg-secondary",
    }),
};

registerField("progressbar", progressBarField);
