import { convertNumericToUnit, getHtmlStyle } from "@html_editor/utils/formatting";
import { Component, useState } from "@odoo/owl";
import { effect } from "@web/core/utils/reactive";
import {
    basicContainerBuilderComponentProps,
    useInputBuilderComponent,
    useBuilderComponent,
    useInputDebouncedCommit,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { BuilderNumberInputBase } from "@html_builder/core/building_blocks/builder_number_input_base";
import { textInputBasePassthroughProps } from "./builder_input_base";
import { useChildRef } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";

export class BuilderNumberInput extends Component {
    static template = "html_builder.BuilderNumberInput";
    static props = {
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
        default: { type: [Number, { value: null }], optional: true },
        unit: { type: String, optional: true },
        saveUnit: { type: String, optional: true },
        step: { type: Number, optional: true },
        min: { type: Number, optional: true },
        max: { type: Number, optional: true },
        composable: { type: Boolean, optional: true },
        applyWithUnit: { type: Boolean, optional: true },
    };
    static components = { BuilderComponent, BuilderNumberInputBase };
    static defaultProps = {
        composable: false,
        applyWithUnit: true,
        default: 0,
    };

    setup() {
        if (this.props.saveUnit && !this.props.unit) {
            throw new Error("'unit' must be defined to use the 'saveUnit' props");
        }

        useBuilderComponent();
        const { state, commit, preview } = useInputBuilderComponent({
            id: this.props.id,
            defaultValue: this.props.default === null ? null : this.props.default?.toString(),
            formatRawValue: this.formatRawValue.bind(this),
            parseDisplayValue: this.parseDisplayValue.bind(this),
        });
        this.commit = commit;
        this.preview = preview;
        this.domState = state;
        this.state = useState({});
        effect(
            ({ value }) => {
                this.state.showUnit = value?.length > 0;
            },
            [state]
        );
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
        if (values === null) {
            return values;
        }
        if (!values) {
            return "";
        }
        return values.trim().split(/\s+/g).map(convertSingleValueFn).join(" ");
    }

    formatRawValue(rawValue) {
        return this.convertSpaceSplitValues(rawValue, (value) => {
            const unit = this.props.unit;
            const { savedValue, savedUnit } = value.match(
                /(?<savedValue>[\d.e+-]+)(?<savedUnit>\w*)/
            ).groups;
            if (savedUnit || this.props.saveUnit) {
                // Convert value from saveUnit to unit
                value = convertNumericToUnit(
                    parseFloat(savedValue),
                    savedUnit || this.props.saveUnit,
                    unit,
                    getHtmlStyle(this.env.getEditingElement().ownerDocument)
                );
            }
            // Put *at most* 3 decimal digits
            return parseFloat(parseFloat(value).toFixed(3)).toString();
        });
    }

    clampValue(value) {
        if (this.props.composable && !value && value !== 0) {
            return value;
        }
        value = parseFloat(value);
        if (value < this.props.min) {
            return `${this.props.min}`;
        }
        if (value > this.props.max) {
            return `${this.props.max}`;
        }
        return +value.toFixed(3);
    }

    parseDisplayValue(displayValue) {
        if (!displayValue) {
            return displayValue;
        }
        if (this.props.composable) {
            displayValue = displayValue
                .trim()
                .replace(/,/g, ".")
                .replace(/[^0-9.-\s]/g, "")
                // Only accept "-" at the start or after a space
                .replace(/(?<!^|\s)-/g, "");
        }
        displayValue =
            displayValue.split(" ").map(this.clampValue.bind(this)).join(" ") || this.props.default;
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
        return this.formatRawValue(this.domState.value);
    }

    updateUnitVisibility(value) {
        if (value === "") {
            this.state.showUnit = false;
        } else {
            const numericValue = Number(value);
            this.state.showUnit = !Number.isNaN(numericValue);
        }
    }

    onChange(e) {
        this.updateUnitVisibility(e.target.value);
    }

    onInput(e) {
        this.updateUnitVisibility(e.target.value);
    }

    onKeydown(e) {
        this.debouncedCommitValue();
    }

    get textInputBaseProps() {
        return pick(this.props, ...Object.keys(textInputBasePassthroughProps));
    }
}
