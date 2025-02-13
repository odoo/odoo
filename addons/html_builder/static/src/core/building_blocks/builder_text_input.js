import { Component } from "@odoo/owl";
import { pick } from "@web/core/utils/objects";
import { BuilderTextInputBase, textInputBasePassthroughProps } from "./builder_text_input_base";
import {
    basicContainerBuilderComponentProps,
    useInputBuilderComponent,
    useBuilderComponent,
} from "./utils";
import { BuilderComponent } from "./builder_component";

export class BuilderTextInput extends Component {
    static template = "html_builder.BuilderTextInput";
    static props = {
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
        default: { type: String, optional: true },
        id: { type: String, optional: true },
    };
    static components = {
        BuilderComponent,
        BuilderTextInputBase,
    };

    setup() {
        useBuilderComponent();
        const { state, onChange, onInput } = useInputBuilderComponent({
            defaultValue: this.props.default,
        });
        this.onChange = onChange;
        this.onInput = onInput;
        this.state = state;
    }

    get textInputBaseProps() {
        return pick(this.props, ...Object.keys(textInputBasePassthroughProps));
    }
}
