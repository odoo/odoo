import { BuilderComponent } from "@html_builder/core/building_blocks/builder_component";
import {
    BuilderTextInputBase,
    textInputBasePassthroughProps,
} from "@html_builder/core/building_blocks/builder_text_input_base";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
    useInputBuilderComponent,
} from "@html_builder/core/building_blocks/utils";
import { Component, useEffect } from "@odoo/owl";
import { useChildRef } from "@web/core/utils/hooks";
import { pick } from "@web/core/utils/objects";
import wUtils from "@website/js/utils";

export class BuilderUrlPicker extends Component {
    static template = "html_builder.BuilderUrlPicker";
    static props = {
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
        id: { type: String, optional: true },
        default: { type: String, optional: true },
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
        });
        this.commit = commit;
        this.preview = preview;
        this.state = state;

        useEffect(
            (inputEl) => {
                if (!inputEl) {
                    return;
                }
                const unmountAutocompleteWithPages = wUtils.autocompleteWithPages(
                    inputEl,
                    {
                        classes: {
                            "ui-autocomplete": "o_website_ui_autocomplete",
                        },
                        body: this.env.getEditingElement().ownerDocument.body,
                        urlChosen: () => {
                            this.commit(this.inputRef.el.value);
                        },
                    },
                    this.env
                );
                return () => unmountAutocompleteWithPages();
            },
            () => [this.inputRef.el]
        );
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
