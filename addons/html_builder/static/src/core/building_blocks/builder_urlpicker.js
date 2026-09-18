import { BuilderComponent } from "@html_builder/core/building_blocks/builder_component";
import { BuilderTextInputBase } from "@html_builder/core/building_blocks/builder_text_input_base";
import { textInputBasePassthroughProps } from "./builder_input_base";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    useInputBuilderComponent,
} from "@html_builder/core/utils";
import { normalizeLinkUrlInput } from "@html_editor/main/link/utils";
import { Component } from "@odoo/owl";
import { useChildRef } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";

export class BuilderUrlPicker extends Component {
    static template = "html_builder.BuilderUrlPicker";
    static props = {
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
        default: { type: String, optional: true },
        previewButton: { type: Boolean, optional: true },
    };
    static defaultProps = {
        previewButton: true,
    };
    static components = {
        BuilderComponent,
        BuilderTextInputBase,
    };

    setup() {
        this.inputRef = useChildRef();
        useBuilderComponent();
        const { state, commit, preview } = useInputBuilderComponent({
            id: this.props.id,
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

    get textInputBaseProps() {
        return pick(this.props, ...Object.keys(textInputBasePassthroughProps));
    }

    openPreviewUrl() {
        if (this.inputRef.el.value) {
            window.open(this.inputRef.el.value, "_blank");
        }
    }
}
