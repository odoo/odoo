import { Component } from "@odoo/owl";
import { pick } from "@web/core/utils/objects";
import { BuilderTextInputBase, textInputBasePassthroughProps } from "./builder_text_input_base";
import {
    basicContainerBuilderComponentProps,
    useInputBuilderComponent,
    useBuilderComponent,
} from "../utils";
import { BuilderComponent } from "./builder_component";

export class BuilderTextInput extends Component {
    static template = "html_builder.BuilderTextInput";
    static props = {
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
        prefix: { type: String, optional: true },
        default: { type: String, optional: true },
    };
    static components = {
        BuilderComponent,
        BuilderTextInputBase,
    };

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

    get textInputBaseProps() {
        return pick(this.props, ...Object.keys(textInputBasePassthroughProps));
    }
}
