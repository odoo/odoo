import { Component } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    useInputBuilderComponent,
    useBuilderComponent,
} from "./utils";
import { BuilderComponent } from "./builder_component";

// TODO: use BuilderTextInputBase
export class BuilderNumberInput extends Component {
    static template = "html_builder.BuilderNumberInput";
    static props = {
        ...basicContainerBuilderComponentProps,
        default: { type: Number, optional: true },
        unit: { type: String, optional: true },
        saveUnit: { type: String, optional: true },
        step: { type: Number, optional: true },
        id: { type: String, optional: true },
        placeholder: { type: String, optional: true },
    };
    static components = { BuilderComponent };

    setup() {
        useBuilderComponent();
        const { state, commit, preview } = useInputBuilderComponent({
            id: this.props.id,
            defaultValue: this.props.default,
        });
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

    // TODO: use this.preview or this.commit?
    handleKeydown(event) {
        if (event.key === "ArrowUp") {
            event.target.value = parseFloat(event.target.value) + (this.props.step || 1);
        } else if (event.key === "ArrowDown") {
            event.target.value = parseFloat(event.target.value) - (this.props.step || 1);
        }
    }
}
