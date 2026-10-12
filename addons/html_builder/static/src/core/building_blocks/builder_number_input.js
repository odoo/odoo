import { BuilderNumberInputBase } from "@html_builder/core/building_blocks/builder_number_input_base";
import { Component, proxy, signal, t, useEffect, useProps } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    useBuilderNumberInputUnits,
    useInputBuilderComponent,
    useInputDebouncedCommit,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { textInputBasePassthroughProps } from "./builder_input_base";

export class BuilderNumberInput extends Component {
    static components = { BuilderComponent, BuilderNumberInputBase };
    static template = "html_builder.BuilderNumberInput";

    props = useProps({
        ...basicContainerBuilderComponentProps,
        default: t.or([t.number(), t.literal(null)]).optional(0),
        unit: t.string().optional(),
        saveUnit: t.string().optional(),
        step: t.number().optional(),
        min: t.number().optional(),
        max: t.number().optional(),
        composable: t.boolean().optional(false),
        applyWithUnit: t.boolean().optional(true),
    });
    textInputBaseProps = useProps(textInputBasePassthroughProps);

    inputRef = signal.ref(HTMLInputElement);

    setup() {
        if (this.props.saveUnit && !this.props.unit) {
            throw new Error("'unit' must be defined to use the 'saveUnit' props");
        }

        const { formatRawValue, parseDisplayValue, clampValue } = useBuilderNumberInputUnits(
            this.props
        );
        this.formatRawValue = formatRawValue;
        this.parseDisplayValue = parseDisplayValue;
        this.clampValue = clampValue;

        useBuilderComponent(this.props);
        const { state, commit, preview } = useInputBuilderComponent(this.props, {
            defaultValue: this.props.default === null ? null : this.props.default?.toString(),
            formatRawValue: this.formatRawValue.bind(this),
            parseDisplayValue: this.parseDisplayValue.bind(this),
        });
        this.commit = commit;
        this.preview = preview;
        this.domState = state;
        this.state = proxy({});
        useEffect(() => {
            this.state.showUnit = state.value?.length > 0;
        });
        this.debouncedCommitValue = useInputDebouncedCommit(this.inputRef, commit);
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

    onKeydownArrow(e) {
        this.debouncedCommitValue();
    }
}
