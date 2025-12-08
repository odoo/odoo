import { Component, useState } from "@odoo/owl";
import { effect } from "@web/core/utils/reactive";
import {
    basicContainerBuilderComponentProps,
    useInputBuilderComponent,
    useBuilderComponent,
    useBuilderNumberInputUnits,
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

        const { formatRawValue, parseDisplayValue, clampValue } = useBuilderNumberInputUnits();
        this.formatRawValue = formatRawValue;
        this.parseDisplayValue = parseDisplayValue;
        this.clampValue = clampValue;

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
