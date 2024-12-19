import { Component } from "@odoo/owl";
import {
    basicContainerWeWidgetProps,
    useInputWeWidget,
    useBuilderComponent,
    BuilderComponent,
} from "../builder_helpers";

export class BuilderTextInput extends Component {
    static template = "html_builder.BuilderTextInput";
    static props = {
        ...basicContainerWeWidgetProps,
        placeholder: { type: String, optional: true },
    };
    static components = { BuilderComponent };

    setup() {
        useBuilderComponent();
        const { state, onChange, onInput } = useInputWeWidget();
        this.onChange = onChange;
        this.onInput = onInput;
        this.state = state;
    }
}
