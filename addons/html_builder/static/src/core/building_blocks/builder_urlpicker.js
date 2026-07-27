import { BuilderComponent } from "@html_builder/core/building_blocks/builder_component";
import { BuilderTextInputBase } from "@html_builder/core/building_blocks/builder_text_input_base";
import { textInputBasePassthroughProps } from "./builder_input_base";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    useInputBuilderComponent,
} from "@html_builder/core/utils";
import { Component, signal } from "@odoo/owl";
import { pick } from "@web/core/utils/objects";

export class BuilderUrlPicker extends Component {
    static template = "html_builder.BuilderUrlPicker";
    static props = {
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
        default: { type: String, optional: true },
    };
    static components = {
        BuilderComponent,
        BuilderTextInputBase,
    };

    setup() {
        this.inputRef = signal.ref();
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

    openPreviewUrl() {
        if (this.inputRef().value) {
            window.open(this.inputRef().value, "_blank");
        }
    }
}
