import { Component } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    useInputBuilderComponent,
    useBuilderComponent,
    BuilderComponent,
} from "../builder_helpers";

export class BuilderTextInput extends Component {
    static template = "html_builder.BuilderTextInput";
    static props = {
        ...basicContainerBuilderComponentProps,
        placeholder: { type: String, optional: true },
    };
    static components = { BuilderComponent };

    setup() {
        useBuilderComponent();
        const { state, onChange, onInput } = useInputBuilderComponent();
        this.onChange = onChange;
        this.onInput = onInput;
        this.state = state;
    }
}
