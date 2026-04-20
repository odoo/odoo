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
        unit: { type: String, optional: true },
        saveUnit: { type: String, optional: true },
        applyWithUnit: { type: Boolean, optional: true },
        withNumberInput: { type: Boolean, optional: true },
        // convertorRatio: controls how values are displayed in input.
        // - Not passed: displays original value
        // - Empty object: displays normalized values from 0-100 range
        // - Custom object: uses provided toRatio/toValue functions
        convertorRatio: {
            type: Object,
            optional: true,
            shape: {
                toRatio: { type: Function, optional: true },
                toValue: { type: Function, optional: true },
                ratioStep: { type: Number, optional: true },
            },
        },
    };
    static defaultProps = {
        ...BuilderComponent.defaultProps,
        min: 0,
        max: 100,
        step: 1,
        default: 0,
        applyWithUnit: true,
        withNumberInput: false,
    };
    static components = { BuilderComponent, BuilderNumberInputBase };

    setup() {
        if (this.props.saveUnit && !this.props.unit) {
            throw new Error("'unit' must be defined to use the 'saveUnit' props");
        }

        if (this.props.convertorRatio && !this.props.withNumberInput) {
            throw new Error("'withNumberInput' must be enabled to use the 'convertorRatio' prop");
        }

        if (this.props.convertorRatio) {
            if (Object.keys(this.props.convertorRatio).length === 0) {
                this.convertorObject = {
                    toRatio: (value) => {
                        const ratioValue =
                            ((parseFloat(value) - this.min) / (this.max - this.min)) * 99 + 1;
                        return Math.round(ratioValue);
                    },
                    toValue: (ratio) => {
                        const originalValue =
                            ((parseFloat(ratio) - 1) / 99) * (this.max - this.min) + this.min;
                        return String(originalValue.toFixed(2));
                    },
                };
            } else {
                this.convertorObject = this.props.convertorRatio;
            }
            if (!this.convertorObject.ratioStep) {
                this.convertorObject.ratioStep = Math.round(
                    (this.props.step / (this.max - this.min)) * (this.maxRatio - this.minRatio)
                );
            }
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
            defaultValue: this.props.default === null ? null : this.props.default?.toString(),
            formatRawValue: this.formatRawValue.bind(this),
            parseDisplayValue: this.parseDisplayValue.bind(this),
        });

        this.inputRefRange = useRef("inputRefRange");
        this.debouncedCommitRangeValue = useInputDebouncedCommit(this.inputRefRange);

        this.commit = commit;
        this.preview = (value, isRatio = false) => {
            if (this.props.withNumberInput) {
                let ratio;
                if (isRatio) {
                    ratio = value;
                    value = this.convertToValue(ratio);
                } else {
                    ratio = this.convertToRatio(value);
                }
                this.inputRefNumber.el.value = ratio;
                // Syncronize the values of range and text inputs during preview
                this.inputRefRange.el.value = value || this.min;
                this.state.value = this.parseDisplayValue(value);
            }
            return preview(value);
        };
        this.state = state;
    }

    convertToRatio(value) {
        if (this.convertorObject) {
            const ratioValue = this.convertorObject.toRatio(value);
            return this.ensureFiniteValue(ratioValue);
        }
        return value;
    }

    convertToValue(ratio) {
        if (ratio && this.convertorObject) {
            const originalValue = this.convertorObject.toValue(ratio);
            return this.ensureFiniteValue(originalValue, { isRatio: false });
        }
        return ratio;
    }

    onChangeRange(e) {
        const normalizedDisplayValue = this.commit(e.target.value);
        e.target.value = normalizedDisplayValue;
    }

    onInputRange(e) {
        this.preview(e.target.value);
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
        // When convertorObject is defined, the input displays ratioed values.
        // So we simply clamp to that range. When false, use the original
        // clampValue.
        if (this.convertorObject) {
            return Math.min(this.maxRatio, Math.max(this.minRatio, value));
        }
        return this.clampValue(value);
    }

    previewInput(ratio) {
        this.preview(ratio, true);
    }

    commitInput(value) {
        const originalValue = value ? this.convertToValue(value) : this.min.toString();
        const committedValue = this.commit(originalValue);
        return this.convertToRatio(committedValue);
    }

    /**
     * Ensures the value is finite. If not, return min in case of -Infinity and
     * max in case of +Infinity.
     *
     * @param {number} value - The value to check.
     * @param {Object} options - Options for the check.
     * @param {boolean} options.isRatio - Whether the value is a ratio.
     * @returns {string} The clamped value as a string.
     */
    ensureFiniteValue(value, { isRatio = true } = {}) {
        if (isRatio) {
            return Math.min(this.maxRatio, Math.max(this.minRatio, value)).toString();
        } else {
            return Math.min(this.max, Math.max(this.min, value)).toString();
        }
    }

    get inputValueRange() {
        return this.formatRawValue(this.state.value || this.min);
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

    get minRatio() {
        return this.convertorObject.toRatio(this.min);
    }

    get maxRatio() {
        return this.convertorObject.toRatio(this.max);
    }

    get textInputBaseProps() {
        return pick(this.props, ...Object.keys(textInputBasePassthroughProps));
    }

    get step() {
        return this.convertorObject ? this.convertorObject.ratioStep : this.props.step;
    }
}
