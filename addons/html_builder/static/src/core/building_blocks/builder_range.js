import { Component } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    useInputBuilderComponent,
} from "./utils";
import { BuilderComponent } from "./builder_component";

// TODO: adapt and use BuilderTextInputBase?
export class BuilderRange extends Component {
    static template = "html_builder.BuilderRange";
    static props = {
        ...basicContainerBuilderComponentProps,
        min: { type: Number, optional: true },
        max: { type: Number, optional: true },
        step: { type: Number, optional: true },
        displayRangeValue: { type: Boolean, optional: true },
        computedOutput: { type: Function, optional: true },
        id: { type: String, optional: true },
        unit: { type: String, optional: true },
    };
    static defaultProps = {
        ...BuilderComponent.defaultProps,
        min: 0,
        max: 100,
        step: 1,
        displayRangeValue: false,
    };
    static components = { BuilderComponent };

    setup() {
        useBuilderComponent();
        const { state, commit, preview } = useInputBuilderComponent({
            id: this.props.id,
            formatRawValue: this.formatRawValue.bind(this),
            parseDisplayValue: this.parseDisplayValue.bind(this),
        });

        this.commit = commit;
        this.preview = preview;
        this.state = state;
    }

    formatRawValue(value) {
        if (this.props.unit) {
            // Remove the unit
            value = value.slice(0, -this.props.unit.length);
        }
        return value;
    }

    parseDisplayValue(value) {
        if (this.props.unit) {
            // Add the unit
            value = `${value}${this.props.unit}`;
        }
        return value;
    }

    onChange(e) {
        const normalizedDisplayValue = this.commit(e.target.value);
        e.target.value = normalizedDisplayValue;
    }

    onInput(e) {
        this.preview(e.target.value);
    }

    get rangeInputValue() {
        return this.state.value ? this.formatRawValue(this.state.value) : "";
    }

    get displayValue() {
        let value = this.rangeInputValue;
        if (this.props.computedOutput) {
            value = this.props.computedOutput(value);
        }
        return value;
    }
}
