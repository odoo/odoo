import { Component, props, proxy, t, useEffect } from "@odoo/owl";
import {
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
    props = props({
        // basicContainerBuilderComponentProps (converted inline)
        id: t.string().optional(),
        applyTo: t.string().optional(),
        preview: t.boolean().optional(),
        inheritedActions: t.array(t.string()).optional(),

        action: t.string().optional(),
        actionParam: t.any().optional(),

        // Shorthand actions.
        classAction: t.any().optional(),
        attributeAction: t.any().optional(),
        dataAttributeAction: t.any().optional(),
        styleAction: t.any().optional(),

        // textInputBasePassthroughProps (converted inline)
        placeholder: t.string().optional(),
        title: t.string().optional(),
        style: t.string().optional(),
        tooltip: t.string().optional(),
        classes: t.string().optional(),
        inputClasses: t.string().optional(),
        prefix: t.string().optional(),
        prefixIcon: t.string().optional(),
        selectTextOnFocus: t.boolean().optional(),

        default: t.or([t.number(), t.literal(null)]).optional(0),
        unit: t.string().optional(),
        saveUnit: t.string().optional(),
        step: t.number().optional(),
        min: t.number().optional(),
        max: t.number().optional(),
        composable: t.boolean().optional(false),
        applyWithUnit: t.boolean().optional(true),
    });
    static components = { BuilderComponent, BuilderNumberInputBase };

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
        this.state = proxy({});
        useEffect(() => {
            this.state.showUnit = state.value?.length > 0;
        });
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

    onKeydownArrow(e) {
        this.debouncedCommitValue();
    }

    get textInputBaseProps() {
        return pick(this.props, ...Object.keys(textInputBasePassthroughProps));
    }
}
