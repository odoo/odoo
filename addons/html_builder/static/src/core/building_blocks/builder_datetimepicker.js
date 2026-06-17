import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { Component, useEffect, proxy, props, t } from "@odoo/owl";
import { ConversionError, formatDate, formatDateTime, parseDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { pick } from "@web/core/utils/objects";
import { useBuilderComponent, useInputBuilderComponent } from "../utils";
import { BuilderComponent } from "./builder_component";
import { BuilderTextInputBase } from "./builder_text_input_base";
import { textInputBasePassthroughProps } from "./builder_input_base";

const { DateTime } = luxon;

export class BuilderDateTimePicker extends Component {
    static template = "html_builder.BuilderDateTimePicker";
    props = props({
        // basicContainerBuilderComponentProps (converted inline)
        id: t.string().optional(),
        applyTo: t.string().optional(),
        preview: t.boolean().optional(),
        inheritedActions: t.array(t.string()).optional(),
        actionParam: t.any().optional(),
        // Shorthand actions.
        classAction: t.any().optional(),
        attributeAction: t.any().optional(),
        dataAttributeAction: t.any().optional(),
        styleAction: t.any().optional(),

        // textInputBasePassthroughProps (converted inline)
        action: t.string().optional(),
        placeholder: t.string().optional(),
        title: t.string().optional(),
        style: t.string().optional(),
        tooltip: t.string().optional(),
        classes: t.string().optional(),
        inputClasses: t.string().optional(),
        prefix: t.string().optional(),
        prefixIcon: t.string().optional(),
        selectTextOnFocus: t.boolean().optional(),

        type: t.selection(["date", "datetime"]).optional("datetime"),
        format: t.string().optional(),
        acceptEmptyDate: t.boolean().optional(true),
    });
    static components = {
        BuilderComponent,
        BuilderTextInputBase,
    };

    setup() {
        useBuilderComponent();
        this.defaultValue = DateTime.now().toUnixInteger().toString();
        const { state, commit, preview } = useInputBuilderComponent({
            id: this.props.id,
            defaultValue: this.props.acceptEmptyDate ? undefined : this.defaultValue,
            formatRawValue: this.formatRawValue.bind(this),
            parseDisplayValue: this.parseDisplayValue.bind(this),
        });
        this.domState = state;
        this.state = proxy({});
        useEffect(() => {
            // State to display in the input.
            this.state.value = state.value;
        });

        this.commit = (userInputValue) => {
            this.isPreviewing = false;
            const result = commit(userInputValue);
            return result;
        };

        this.preview = (userInputValue) => {
            this.isPreviewing = true;
            preview(userInputValue);
        };

        const minDate = DateTime.fromObject({ year: 1000 });
        const maxDate = DateTime.now().plus({ year: 200 });
        const getPickerProps = () => ({
            type: this.props.type,
            minDate,
            maxDate,
            value: this.getCurrentValueDateTime(),
            rounding: 1,
        });

        const isDateOnly = this.props.type === "date";
        this.formatDateTime = isDateOnly ? formatDate : formatDateTime;
        this.format = isDateOnly
            ? localization.dateFormat
            : localization.dateTimeFormat.replace(":ss", "").replace(".ss", "");

        this.dateTimePicker = useDateTimePicker({
            target: "root",
            format: this.props.format,
            get pickerProps() {
                return getPickerProps();
            },
            onApply: (value) => {
                this.commit(this.formatDateTime(value));
            },
            onChange: (value) => {
                const dateString = this.formatDateTime(value);
                this.preview(dateString);
                this.state.value = this.parseDisplayValue(dateString);
            },
        });
    }

    /**
     * @returns {DateTime} the current value of the datetime picker
     */
    getCurrentValueDateTime() {
        return this.domState.value ? DateTime.fromSeconds(parseInt(this.domState.value)) : false;
    }

    /**
     * @param {String} rawValue - the raw value in seconds
     * @returns {String} a formatted date string
     */
    formatRawValue(rawValue) {
        return rawValue
            ? this.formatDateTime(DateTime.fromSeconds(parseInt(rawValue)), { format: this.format })
            : "";
    }

    /**
     * @param {String} displayValue - representing a date
     * @returns {String} number of seconds
     */
    parseDisplayValue(displayValue) {
        if (displayValue === "" && this.props.acceptEmptyDate) {
            return undefined;
        }
        try {
            const parsedDateTime = parseDateTime(displayValue);
            if (parsedDateTime) {
                return parsedDateTime.set({ second: 0, millisecond: 0 }).toUnixInteger().toString();
            }
        } catch (e) {
            // A ConversionError means displayValue is an invalid date: fall
            // back to default value.
            if (!(e instanceof ConversionError)) {
                throw e;
            }
            if (!this.isPreviewing && displayValue !== "") {
                return this.domState.value;
            }
        }
        return this.defaultValue;
    }

    /**
     * @returns {String} a formatted date string
     */
    get displayValue() {
        return this.state.value !== undefined ? this.formatRawValue(this.state.value) : undefined;
    }

    get textInputBaseProps() {
        return pick(this.props, ...Object.keys(textInputBasePassthroughProps));
    }

    onFocus() {
        this.dateTimePicker.open();
    }
}
