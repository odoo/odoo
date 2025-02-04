import { Component } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    useInputBuilderComponent,
    useBuilderComponent,
} from "./utils";
import { BuilderComponent } from "./builder_component";

export class BuilderNumberInput extends Component {
    static template = "html_builder.BuilderNumberInput";
    static props = {
        ...basicContainerBuilderComponentProps,
        default: { type: Number, optional: true },
        unit: { type: String, optional: true },
        saveUnit: { type: String, optional: true },
        step: { type: Number, optional: true },
        id: { type: String, optional: true },
    };
    static components = { BuilderComponent };

    setup() {
        useBuilderComponent();
        const { state, onChange, onInput } = useInputBuilderComponent({
            defaultValue: this.props.default,
        });
        this.onChange = onChange;
        this.onInput = onInput;
        this.state = state;
    }

    handleKeydown(event) {
        if (event.key === "ArrowUp") {
            event.target.value = parseFloat(event.target.value) + (this.props.step || 1);
        } else if (event.key === "ArrowDown") {
            event.target.value = parseFloat(event.target.value) - (this.props.step || 1);
        }
    }
}
