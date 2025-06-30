import { convertNumericToUnit, getHtmlStyle } from "@html_editor/utils/formatting";
import { Component } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    useInputBuilderComponent,
    useBuilderComponent,
    useInputDebouncedCommit,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import {
    BuilderTextInputBase,
    textInputBasePassthroughProps,
} from "@html_builder/core/building_blocks/builder_text_input_base";
import { useChildRef } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";

export class BuilderNumberInput extends Component {
    static template = "html_builder.BuilderNumberInput";
    static props = {
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
        default: { type: Number, optional: true },
        unit: { type: String, optional: true },
        saveUnit: { type: String, optional: true },
        step: { type: Number, optional: true },
        min: { type: Number, optional: true },
        max: { type: Number, optional: true },
        composable: { type: Boolean, optional: true },
        applyWithUnit: { type: Boolean, optional: true },
    };
    static components = { BuilderComponent, BuilderTextInputBase };
    static defaultProps = {
        composable: false,
        applyWithUnit: true,
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

        this.inputRef = useChildRef();
        this.debouncedCommitValue = useInputDebouncedCommit(this.inputRef);
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
                value = convertNumericToUnit(
                    value,
                    saveUnit,
                    unit,
                    getHtmlStyle(this.env.getEditingElement().ownerDocument)
                );
            }
            return value;
        });
    }

    clampValue(value) {
        if (parseFloat(value) < this.props.min) {
            return `${this.props.min}`;
        }
        if (parseFloat(value) > this.props.max) {
            return `${this.props.max}`;
        }
        return value;
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
        displayValue = displayValue.split(" ").map(this.clampValue.bind(this)).join(" ");

        return this.convertSpaceSplitValues(displayValue, (value) => {
            if (value === "") {
                return value;
            }
            const unit = this.props.unit;
            const saveUnit = this.props.saveUnit;
            const applyWithUnit = this.props.applyWithUnit;
            if (unit && saveUnit) {
                // Convert value from unit to saveUnit
                value = convertNumericToUnit(
                    value,
                    unit,
                    saveUnit,
                    getHtmlStyle(this.env.getEditingElement().ownerDocument)
                );
            }
            if (unit && applyWithUnit) {
                if (saveUnit || saveUnit === "") {
                    value = value + saveUnit;
                } else {
                    value = value + unit;
                }
            }
            return value;
        });
    }

    get displayValue() {
        return this.formatRawValue(this.state.value);
    }

    onKeydown(e) {
        if (!["ArrowUp", "ArrowDown"].includes(e.key)) {
            return;
        }
        const values = e.target.value.split(" ").map((number) => parseFloat(number) || 0);
        if (e.key === "ArrowUp") {
            values.forEach((value, i) => {
                values[i] = this.clampValue(value + (this.props.step || 1));
            });
        } else if (e.key === "ArrowDown") {
            values.forEach((value, i) => {
                values[i] = this.clampValue(value - (this.props.step || 1));
            });
        }
        e.target.value = values.join(" ");
        this.preview(e.target.value);
        this.debouncedCommitValue();
    }

    get textInputBaseProps() {
        return pick(this.props, ...Object.keys(textInputBasePassthroughProps));
    }
}
