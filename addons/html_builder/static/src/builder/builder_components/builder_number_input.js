import { Component } from "@odoo/owl";
import {
    basicContainerWeWidgetProps,
    useInputWeWidget,
    useBuilderComponent,
    BuilderComponent,
} from "../builder_helpers";

export class BuilderNumberInput extends Component {
    static template = "html_builder.BuilderNumberInput";
    static props = {
        ...basicContainerWeWidgetProps,
        unit: { type: String, optional: true },
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
