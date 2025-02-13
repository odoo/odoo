import { Component } from "@odoo/owl";
import { useDateTimePicker } from "@web/core/datetime/datetime_hook";
import { ConversionError, formatDateTime, parseDateTime } from "@web/core/l10n/dates";
import { pick } from "@web/core/utils/objects";
import { BuilderComponent } from "./builder_component";
import { BuilderTextInputBase, textInputBasePassthroughProps } from "./builder_text_input_base";
import { basicContainerBuilderComponentProps, useBuilderComponent, useInputBuilderComponent } from "./utils";

const { DateTime } = luxon;

// TODO: refactor useInputBuilderComponent api to avoid hacking with events
export class BuilderDateTimePicker extends Component {
    static template = "html_builder.BuilderDateTimePicker";
    static props = {
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
        default: { type: String, optional: true },
        id: { type: String, optional: true },
        type: { type: [{ value: "date" }, { value: "datetime" }], optional: true },
        format: { type: String, optional: true },
    };
    static defaultProps = {
        type: "datetime",
    };
    static components = {
        BuilderComponent,
        BuilderTextInputBase,
    };

    setup() {
        useBuilderComponent();
        const { state, onChange, onInput } = useInputBuilderComponent({
            defaultValue: this.props.default,
            formatRawValue: this.formatRawValue.bind(this),
            parseDisplayValue: this.parseDisplayValue.bind(this),
        });
        this.onChange = onChange;
        this.onInput = onInput;
        this.state = state;

        const getPickerProps = () => ({
            type: this.props.type,
            minDate: DateTime.fromObject({ year: 1000 }),
            maxDate: DateTime.now().plus({ year: 200 }),
            value: this.getCurrentValueDateTime(),
            rounding: 0,
        });

        this.dateTimePicker = useDateTimePicker({
            target: "root",
            format: this.props.format,
            get pickerProps() {
                return getPickerProps();
            },
            onApply: (value) => {
                this.inputRef.el.value = formatDateTime(value);
                this.inputRef.el.dispatchEvent(new Event("change"));
            },
            onChange: (value) => {
                this.inputRef.el.value = formatDateTime(value);
                this.inputRef.el.dispatchEvent(new Event("input"));
            },
        });
    }

    getDefaultValue() {
        if (this.props.default === "now") {
            return DateTime.now().toUnixInteger().toString();
        } else {
            return undefined;
        }
    }

    getCurrentValueDateTime() {
        let value = this.state.value;
        if (this.state.value === undefined) {
            value = this.getDefaultValue();
        }
        return value !== undefined
            ? DateTime.fromSeconds(parseInt(value))
            : undefined;
    }

    formatRawValue(rawValue) {
        return formatDateTime(DateTime.fromSeconds(parseInt(rawValue)));
    }

    parseDisplayValue(displayValue) {
        try {
            const parsedDateTime = parseDateTime(displayValue);
            if (parsedDateTime) {
                return parsedDateTime.toUnixInteger().toString();
            }
        } catch (e) {
            // A ConversionError means displayValue is an invalid date: fall
            // back to default value.
            if (!(e instanceof ConversionError)) {
                throw e;
            }
        }
        return this.getDefaultValue();
    }

    get displayValue() {
        return this.state.value !== undefined
            ? this.formatRawValue(this.state.value)
            : undefined;
    }

    get textInputBaseProps() {
        return pick(this.props, ...Object.keys(textInputBasePassthroughProps));
    }

    setInputRef(ref) {
        this.inputRef = ref;
    }

    onFocus() {
        this.dateTimePicker.open();
    }
}
