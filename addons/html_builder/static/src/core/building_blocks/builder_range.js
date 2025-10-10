import { Component, useRef } from "@odoo/owl";
import { convertNumericToUnit, getHtmlStyle } from "@html_editor/utils/formatting";
import {
    basicContainerBuilderComponentProps,
    useActionInfo,
    useBuilderComponent,
    useInputBuilderComponent,
    useInputDebouncedCommit,
} from "../utils";
import { BuilderComponent } from "./builder_component";

export class BuilderRange extends Component {
    static template = "html_builder.BuilderRange";
    static props = {
        ...basicContainerBuilderComponentProps,
        min: { type: Number, optional: true },
        max: { type: Number, optional: true },
        step: { type: Number, optional: true },
        displayRangeValue: { type: Boolean, optional: true },
        computedOutput: { type: Function, optional: true },
        unit: { type: String, optional: true },
        saveUnit: { type: String, optional: true },
        applyWithUnit: { type: Boolean, optional: true },
        classes: { type: String, optional: true },
    };
    static defaultProps = {
        ...BuilderComponent.defaultProps,
        min: 0,
        max: 100,
        step: 1,
        displayRangeValue: false,
        applyWithUnit: true,
    };
    static components = { BuilderComponent };

    setup() {
        if (this.props.saveUnit && !this.props.unit) {
            throw new Error("'unit' must be defined to use the 'saveUnit' props");
        }

        this.info = useActionInfo();
        useBuilderComponent();
        const { state, commit, preview } = useInputBuilderComponent({
            id: this.props.id,
            formatRawValue: this.formatRawValue.bind(this),
            parseDisplayValue: this.parseDisplayValue.bind(this),
        });

        this.inputRef = useRef("inputRef");
        this.debouncedCommitValue = useInputDebouncedCommit(this.inputRef);

        this.commit = commit;
        this.preview = preview;
        this.state = state;
    }

    formatRawValue(value) {
        const { unit, saveUnit } = this.props;
        if (!value || !unit) {
            return value;
        }
        if (saveUnit) {
            const match = value.match(/(?<savedValue>[\d.e+-]+)(?<savedUnit>\w*)/);
            if (!match?.groups) {
                return value;
            }
            const { savedValue, savedUnit } = match.groups;
            const numericValue = parseFloat(savedValue);
            if (Number.isNaN(numericValue)) {
                return value;
            }
            const convertedValue = convertNumericToUnit(
                numericValue,
                savedUnit || saveUnit,
                unit,
                getHtmlStyle(this.env.getEditingElement().ownerDocument)
            );
            return `${convertedValue}`;
        }
        return value.endsWith(unit) ? value.slice(0, -unit.length) : value;
    }

    parseDisplayValue(value) {
        if (!value) {
            return value;
        }

        const { unit, saveUnit, applyWithUnit } = this.props;

        let out = value;
        if (unit && saveUnit) {
            const num = typeof value === "number" ? value : parseFloat(value);
            const style = getHtmlStyle(this.env.getEditingElement().ownerDocument);
            out = convertNumericToUnit(num, unit, saveUnit, style);
        }

        const suffix = unit && applyWithUnit ? saveUnit ?? unit : "";
        return `${out}${suffix}`;
    }

    onChange(e) {
        const normalizedDisplayValue = this.commit(e.target.value);
        e.target.value = normalizedDisplayValue;
    }

    onInput(e) {
        this.preview(e.target.value);
        if (this.props.displayRangeValue) {
            this.state.value = this.parseDisplayValue(e.target.value);
        }
    }

    onKeydown(e) {
        if (!["ArrowLeft", "ArrowUp", "ArrowDown", "ArrowRight"].includes(e.key)) {
            return;
        }
        e.preventDefault();
        let value = parseInt(e.target.value);
        if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
            value = Math.max(this.min, value - this.props.step);
        } else {
            value = Math.min(this.max, value + this.props.step);
        }
        e.target.value = value;
        this.onInput(e);
        this.debouncedCommitValue();
    }

    get rangeInputValue() {
        return this.state.value ? this.formatRawValue(this.state.value) : "0";
    }

    get displayValue() {
        let value = this.rangeInputValue;
        if (this.props.computedOutput) {
            value = this.props.computedOutput(value);
        } else if (this.props.unit) {
            value = `${value}${this.props.unit}`;
        }
        return value;
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
}
