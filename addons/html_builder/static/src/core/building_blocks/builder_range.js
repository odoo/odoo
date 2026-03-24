import { useRef } from "@web/owl2/utils";
import { Component } from "@odoo/owl";
import { useChildRef } from "@web/core/utils/hooks";
import {
    basicContainerBuilderComponentProps,
    useActionInfo,
    useBuilderComponent,
    useInputBuilderComponent,
    useInputDebouncedCommit,
    useBuilderNumberInputUnits,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { BuilderNumberInputBase } from "./builder_number_input_base";
import { textInputBasePassthroughProps } from "./builder_input_base";
import { pick } from "@web/core/utils/objects";

export class BuilderRange extends Component {
    static template = "html_builder.BuilderRange";
    static props = {
        ...basicContainerBuilderComponentProps,
        min: { type: Number, optional: true },
        max: { type: Number, optional: true },
        step: { type: Number, optional: true },
        default: { type: Number, optional: true },
        displayRangeValue: { type: Boolean, optional: true },
        computedOutput: { type: Function, optional: true },
        unit: { type: String, optional: true },
        saveUnit: { type: String, optional: true },
        applyWithUnit: { type: Boolean, optional: true },
        withNumberInput: { type: Boolean, optional: true },
        displayNormalizedValue: { type: Boolean, optional: true },
    };
    static defaultProps = {
        ...BuilderComponent.defaultProps,
        min: 0,
        max: 100,
        step: 1,
        default: 0,
        displayRangeValue: false,
        applyWithUnit: true,
        withNumberInput: false,
        displayNormalizedValue: false,
    };
    static components = { BuilderComponent, BuilderNumberInputBase };

    setup() {
        if (this.props.saveUnit && !this.props.unit) {
            throw new Error("'unit' must be defined to use the 'saveUnit' props");
        }

        if (this.props.displayNormalizedValue && !this.props.withNumberInput) {
            throw new Error(
                "'withNumberInput' must be enabled to use the 'displayNormalizedValue' prop"
            );
        }

        if (this.props.withNumberInput) {
            this.inputRefNumber = useChildRef();
            this.debouncedCommitNumberValue = useInputDebouncedCommit(this.inputRefNumber);
        }

        const { formatRawValue, parseDisplayValue, clampValue } = useBuilderNumberInputUnits();
        this.formatRawValue = formatRawValue;
        this.parseDisplayValue = parseDisplayValue;
        this.clampValue = clampValue;

        this.info = useActionInfo();
        useBuilderComponent();
        const { state, commit, preview } = useInputBuilderComponent({
            id: this.props.id,
            formatRawValue: this.formatRawValue.bind(this),
            parseDisplayValue: this.parseDisplayValue.bind(this),
        });

        this.inputRefRange = useRef("inputRefRange");
        this.debouncedCommitRangeValue = useInputDebouncedCommit(this.inputRefRange);

        this.commit = commit;
        this.preview = (value) => {
            if (this.props.withNumberInput) {
                // Syncronize the values of range and text inputs during preview
                this.inputRefNumber.el.value = this.convertToRatio(value);
                this.inputRefRange.el.value = value || this.min;
                this.state.value = this.parseDisplayValue(value);
            }
            return preview(value);
        };
        this.state = state;
    }

    convertToRatio(value) {
        if (!this.props.displayNormalizedValue || !value) {
            return value;
        }
        const ratioValue = ((parseFloat(value) - this.min) / (this.max - this.min)) * 99 + 1;
        return Math.round(ratioValue);
    }

    convertToValue(ratio) {
        if (!this.props.displayNormalizedValue || !ratio) {
            return String(ratio);
        }
        const originalValue = ((parseFloat(ratio) - 1) / 99) * (this.max - this.min) + this.min;
        return String(originalValue.toFixed(2));
    }

    onChangeRange(e) {
        const normalizedDisplayValue = this.commit(e.target.value);
        e.target.value = normalizedDisplayValue;
    }

    onInputRange(e) {
        this.preview(e.target.value);
        if (this.props.displayRangeValue) {
            this.state.value = this.parseDisplayValue(e.target.value);
        }
    }

    onKeydownRange(e) {
        if (!["ArrowLeft", "ArrowUp", "ArrowDown", "ArrowRight"].includes(e.key)) {
            return;
        }
        e.preventDefault();
        let value = parseFloat(e.target.value);
        if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
            value = Math.max(this.min, value - this.props.step);
        } else {
            value = Math.min(this.max, value + this.props.step);
        }
        e.target.value = value;
        this.onInputRange(e);
        this.debouncedCommitRangeValue();
    }

    onKeydownNumber() {
        this.debouncedCommitNumberValue();
    }

    clampValueForInput(value) {
        // When displayNormalizedValue is true, the input displays ratioed
        // values. So we simply clamp to that range. When false, use the
        // original clampValue.
        if (this.props.displayNormalizedValue) {
            return Math.min(100, Math.max(1, value));
        }
        return this.clampValue(value);
    }

    previewInput(ratio) {
        this.preview(this.convertToValue(ratio));
    }

    commitInput(value) {
        const originalValue = value ? this.convertToValue(value) : this.min.toString();
        const committedValue = this.commit(originalValue);
        return this.convertToRatio(committedValue);
    }

    get inputValueRange() {
        return this.formatRawValue(this.state.value || this.min);
    }

    get displayValueRange() {
        let value = this.inputValueRange;
        if (this.props.computedOutput) {
            value = this.props.computedOutput(value);
        } else if (this.props.unit) {
            value = `${value}${this.props.unit}`;
        }
        return value;
    }

    get displayValueNumber() {
        return this.formatRawValue(this.convertToRatio(this.state.value || this.min));
    }

    get className() {
        const baseClasses = "p-0 border-0";
        return this.props.min > this.props.max ? `${baseClasses} o_we_inverted_range` : baseClasses;
    }

    get min() {
        return this.props.min > this.props.max ? this.props.max : this.props.min;
    }

    get max() {
        return this.props.min > this.props.max ? this.props.min : this.props.max;
    }

    get textInputBaseProps() {
        return pick(this.props, ...Object.keys(textInputBasePassthroughProps));
    }

    get step() {
        return this.props.displayNormalizedValue
            ? Math.round((this.props.step / (this.max - this.min)) * 99)
            : this.props.step;
    }
}
