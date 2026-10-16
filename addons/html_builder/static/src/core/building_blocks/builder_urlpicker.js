import { BuilderComponent } from "@html_builder/core/building_blocks/builder_component";
import { BuilderTextInputBase } from "@html_builder/core/building_blocks/builder_text_input_base";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    useInputBuilderComponent,
} from "@html_builder/core/utils";
import { normalizeLinkUrlInput } from "@html_editor/main/link/utils";
import { Component, signal, t, useProps } from "@odoo/owl";
import { textInputBasePassthroughProps } from "./builder_input_base";

export class BuilderUrlPicker extends Component {
    static components = {
        BuilderComponent,
        BuilderTextInputBase,
    };
    static template = "html_builder.BuilderUrlPicker";

    props = useProps({
        ...basicContainerBuilderComponentProps,
        default: t.string().optional(),
        previewButton: t.boolean().optional(true),
    });
    textInputBaseProps = useProps(textInputBasePassthroughProps);

    inputRef = signal.ref(HTMLInputElement);

    setup() {
        useBuilderComponent(this.props);
        const { state, commit, preview } = useInputBuilderComponent(this.props, {
            defaultValue: this.props.default,
            parseDisplayValue: this.parseDisplayValue.bind(this),
        });
        this.commit = commit;
        this.preview = preview;
        this.state = state;
    }

    parseDisplayValue(value) {
        return normalizeLinkUrlInput(value, { href: this.state.value || "" });
    }
    openPreviewUrl() {
        if (this.inputRef().value) {
            window.open(this.inputRef().value, "_blank");
        }
    }
}
