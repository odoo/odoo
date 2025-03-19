import { Component } from "@odoo/owl";
import { useDateTimePicker } from "@web/core/datetime/datetime_hook";
import { ConversionError, formatDateTime, parseDateTime } from "@web/core/l10n/dates";
import { pick } from "@web/core/utils/objects";
import { BuilderComponent } from "./builder_component";
import { BuilderTextInputBase, textInputBasePassthroughProps } from "./builder_text_input_base";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    useInputBuilderComponent,
} from "../utils";

const { DateTime } = luxon;

export class BuilderDateTimePicker extends Component {
    static template = "html_builder.BuilderDateTimePicker";
    static props = {
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
        id: { type: String, optional: true },
        default: { type: String, optional: true },
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
        const { state, commit, preview } = useInputBuilderComponent({
            id: this.props.id,
            defaultValue: this.props.default,
            formatRawValue: this.formatRawValue.bind(this),
            parseDisplayValue: this.parseDisplayValue.bind(this),
        });
        this.commit = commit;
        this.preview = preview;
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
                this.commit(formatDateTime(value));
            },
            onChange: (value) => {
                this.preview(formatDateTime(value));
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
        return value !== undefined ? DateTime.fromSeconds(parseInt(value)) : undefined;
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
        return this.state.value !== undefined ? this.formatRawValue(this.state.value) : undefined;
    }

    get textInputBaseProps() {
        return pick(this.props, ...Object.keys(textInputBasePassthroughProps));
    }

    onFocus() {
        this.dateTimePicker.open();
    }
}
