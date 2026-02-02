import { Component, useRef } from "@odoo/owl";
import { useChildRef } from "@web/core/utils/hooks";
import {
    basicContainerBuilderComponentProps,
    useActionInfo,
    useBuilderComponent,
    useInputBuilderComponent,
    useInputDebouncedCommit,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { textInputBasePassthroughProps } from "./builder_input_base";
import { pick } from "@web/core/utils/objects";

export class BuilderRangeSelect extends Component {
    static template = "html_builder.BuilderRangeSelect";
    static props = {
        ...basicContainerBuilderComponentProps,
        values: { type: Array, optional: false },
        default: { type: String, optional: false },
    };
    static defaultProps = {
        ...BuilderComponent.defaultProps,
    };
    static components = { BuilderComponent };

    setup() {
        if (this.props.saveUnit && !this.props.unit) {
            throw new Error("'unit' must be defined to use the 'saveUnit' props");
        }

        if (this.props.withNumberInput) {
            this.inputRefNumber = useChildRef();
            this.debouncedCommitNumberValue = useInputDebouncedCommit(this.inputRefNumber);
        }

        this.info = useActionInfo();
        useBuilderComponent();
        const { state, commit, preview } = useInputBuilderComponent({
            id: this.props.id,
        });

        this.inputRefRange = useRef("inputRefRange");
        this.debouncedCommitRangeValue = useInputDebouncedCommit(this.inputRefRange);

        this.commit = (value) => commit(this.props.values[value]);
        this.preview = (value) => preview(this.props.values[value]);
        this.state = state;
    }

    onChangeRange(e) {
        const normalizedDisplayValue = this.commit(e.target.value);
        e.target.value = normalizedDisplayValue;
    }

    onInputRange(e) {
        this.preview(e.target.value);
        if (this.props.displayRangeValue) {
            this.state.value = e.target.value;
        }
    }

    onKeydownRange(e) {
        if (!["ArrowLeft", "ArrowUp", "ArrowDown", "ArrowRight"].includes(e.key)) {
            return;
        }
        e.preventDefault();
        let value = parseFloat(e.target.value);
        if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
            value = Math.max(0, value - 1);
        } else {
            value = Math.min(this.props.values.length - 1, value + 1);
        }
        e.target.value = value;
        this.onInputRange(e);
        this.debouncedCommitRangeValue();
    }

    onKeydownNumber() {
        this.debouncedCommitNumberValue();
    }

    get inputValueRange() {
        return this.state.value ? this.state.value : "0";
    }

    get displayValueRange() {
        return this.inputValueRange;
    }

    get className() {
        return "p-0 border-0";
    }

    get textInputBaseProps() {
        return pick(this.props, ...Object.keys(textInputBasePassthroughProps));
    }
}
