import { Component } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    BuilderComponent,
    useBuilderComponent,
    useInputBuilderComponent,
} from "./utils";

export class BuilderRange extends Component {
    static template = "html_builder.BuilderRange";
    static props = {
        ...basicContainerBuilderComponentProps,
        min: { type: Number, optional: true },
        max: { type: Number, optional: true },
        step: { type: Number, optional: true },
        displayRangeValue: { type: Boolean, optional: true },
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
        const { state, onChange, onInput } = useInputBuilderComponent();

        this.onChange = onChange;
        this.onInput = (e) => {
            this.state.value = e.target.value;
            onInput(e);
        };
        this.state = state;
    }
}
