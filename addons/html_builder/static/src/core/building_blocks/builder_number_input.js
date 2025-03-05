import { convertNumericToUnit } from "@html_editor/utils/formatting";
import { Component } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    useInputBuilderComponent,
    useBuilderComponent,
} from "./utils";
import { BuilderComponent } from "./builder_component";

// TODO: use BuilderTextInputBase
export class BuilderNumberInput extends Component {
    static template = "html_builder.BuilderNumberInput";
    static props = {
        ...basicContainerBuilderComponentProps,
        default: { type: Number, optional: true },
        unit: { type: String, optional: true },
        saveUnit: { type: String, optional: true },
        step: { type: Number, optional: true },
        id: { type: String, optional: true },
        placeholder: { type: String, optional: true },
        style: { type: String, optional: true },
        composable: { type: Boolean, optional: true },
        // TODO support a min and max value
    };
    static components = { BuilderComponent };
    static defaultProps = {
        composable: false,
    };

    setup() {
        if (this.props.saveUnit && !this.props.unit) {
            throw new Error("'unit' must be defined to use the 'saveUnit' props");
        }

        useBuilderComponent();
        const { state, commit, preview } = useInputBuilderComponent({
            id: this.props.id,
            defaultValue: this.props.default?.toString(),
            formatRawValue: this.formatRawValue.bind(this),
            parseDisplayValue: this.parseDisplayValue.bind(this),
        });
        this.commit = commit;
        this.preview = preview;
        this.state = state;
    }

    /**
     * @param {string | number} values - Values separated by spaces or a number
     * @param {(string) => string} convertSingleValueFn - Convert a single value
     */
    convertSpaceSplitValues(values, convertSingleValueFn) {
        if (typeof values === "number") {
            return convertSingleValueFn(values.toString());
        }
        if (!values) {
            return "";
        }
        return values.trim().split(/\s+/g).map(convertSingleValueFn).join(" ");
    }

    formatRawValue(rawValue) {
        return this.convertSpaceSplitValues(rawValue, (value) => {
            const unit = this.props.unit;
            const saveUnit = this.props.saveUnit;
            // Remove the unit
            value = value.match(/[\d.e+-]+/g)[0];
            if (saveUnit) {
                // Convert value from saveUnit to unit
                value = convertNumericToUnit(value, saveUnit, unit);
            }
            return value;
        });
    }

    parseDisplayValue(displayValue) {
        displayValue = displayValue.replace(/,/g, ".");
        // Only accept 0-9, dot, - sign and space if multiple values are allowed
        if (this.props.composable) {
            displayValue = displayValue.replace(/[^0-9.-\s]/g, "");
        } else {
            displayValue = displayValue
                .trim()
                .split(" ")[0]
                .replace(/[^0-9.-]/g, "");
        }

        return this.convertSpaceSplitValues(displayValue, (value) => {
            if (value === "") {
                return value;
            }
            const unit = this.props.unit;
            const saveUnit = this.props.saveUnit;
            if (unit && saveUnit) {
                // Convert value from unit to saveUnit
                value = convertNumericToUnit(value, unit, saveUnit);
            }
            if (unit) {
                if (saveUnit || saveUnit === "") {
                    value = value + saveUnit;
                } else {
                    value = value + unit;
                }
            }
            return value;
        });
    }

    onChange(e) {
        const normalizedDisplayValue = this.commit(e.target.value);
        e.target.value = normalizedDisplayValue;
    }

    onInput(e) {
        this.preview(e.target.value);
    }

    get displayValue() {
        return this.formatRawValue(this.state.value);
    }

    // TODO: use this.preview or this.commit?
    onKeydown(e) {
        if (!["ArrowUp", "ArrowDown"].includes(e.key)) {
            return;
        }
        const values = e.target.value.split(" ").map((number) => parseFloat(number) || 0);
        if (e.key === "ArrowUp") {
            values.forEach((value, i) => {
                values[i] = value + (this.props.step || 1);
            });
        } else if (e.key === "ArrowDown") {
            values.forEach((value, i) => {
                values[i] = value - (this.props.step || 1);
            });
        }
        e.target.value = values.join(" ");
        // OK because it only uses event.target.value.
        this.onChange(e);
    }
}
