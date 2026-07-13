import { BuilderComponent } from "@html_builder/core/building_blocks/builder_component";
import { BuilderTextInputBase } from "@html_builder/core/building_blocks/builder_text_input_base";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    useInputBuilderComponent,
} from "@html_builder/core/utils";
<<<<<<< 2aeace2f0d103e67b0593eeb89a66cc990b77783
import { Component, signal, t, useProps } from "@odoo/owl";
import { textInputBasePassthroughProps } from "./builder_input_base";
||||||| e678c8dc2e67b80037e84ca3aca2a8571e33d258
import { Component } from "@odoo/owl";
import { useChildRef } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";
=======
import { normalizeLinkUrlInput } from "@html_editor/main/link/utils";
import { Component } from "@odoo/owl";
import { useChildRef } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";
>>>>>>> 45b27de266805f995b4d84bbedce3f2c3548ab7c

export class BuilderUrlPicker extends Component {
<<<<<<< 2aeace2f0d103e67b0593eeb89a66cc990b77783
||||||| e678c8dc2e67b80037e84ca3aca2a8571e33d258
    static template = "html_builder.BuilderUrlPicker";
    static props = {
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
        default: { type: String, optional: true },
    };
=======
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
>>>>>>> 45b27de266805f995b4d84bbedce3f2c3548ab7c
    static components = {
        BuilderComponent,
        BuilderTextInputBase,
    };
    static template = "html_builder.BuilderUrlPicker";

    props = useProps({
        ...basicContainerBuilderComponentProps,
        default: t.string().optional(),
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

<<<<<<< 2aeace2f0d103e67b0593eeb89a66cc990b77783
||||||| e678c8dc2e67b80037e84ca3aca2a8571e33d258
    get textInputBaseProps() {
        return pick(this.props, ...Object.keys(textInputBasePassthroughProps));
    }

=======
    parseDisplayValue(value) {
        return normalizeLinkUrlInput(value, { href: this.state.value || "" });
    }

    get textInputBaseProps() {
        return pick(this.props, ...Object.keys(textInputBasePassthroughProps));
    }

>>>>>>> 45b27de266805f995b4d84bbedce3f2c3548ab7c
    openPreviewUrl() {
        if (this.inputRef().value) {
            window.open(this.inputRef().value, "_blank");
        }
    }
}
