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
        const { state, commit, preview } = useInputBuilderComponent({ id: this.props.id });

        this.commit = commit;
        this.preview = preview;
        this.state = state;
    }

    onChange(e) {
        const normalizedDisplayValue = this.commit(e.target.value);
        e.target.value = normalizedDisplayValue;
    }

    onInput(e) {
        this.preview(e.target.value);
    }

    getOutput(value) {
        // TODO: adapt when agau's PR that adapts `useInputBuilderComponent` is
        // merged.
        return this.props.computedOutput ? this.props.computedOutput(value) : value;
    }
}
