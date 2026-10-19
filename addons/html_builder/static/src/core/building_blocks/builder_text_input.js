import { Component, t, useProps } from "@odoo/owl";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    useInputBuilderComponent,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { textInputBasePassthroughProps } from "./builder_input_base";
import { BuilderTextInputBase } from "./builder_text_input_base";

export class BuilderTextInput extends Component {
    static components = {
        BuilderComponent,
        BuilderTextInputBase,
    };
    static template = "html_builder.BuilderTextInput";

    props = useProps({
        ...basicContainerBuilderComponentProps,
        default: t.string().optional(),
    });
    textInputBaseProps = useProps(textInputBasePassthroughProps);

    setup() {
        useBuilderComponent(this.props);
        const { state, commit, preview } = useInputBuilderComponent(this.props, {
            defaultValue: this.props.default,
        });
        this.commit = commit;
        this.preview = preview;
        this.state = state;
    }
}
