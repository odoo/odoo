import { BuilderComponent } from "@html_builder/core/building_blocks/builder_component";
import {
    BuilderTextInputBase,
    textInputBasePassthroughProps,
} from "@html_builder/core/building_blocks/builder_text_input_base";
import {
    basicContainerBuilderComponentProps,
    useBuilderComponent,
} from "@html_builder/core/utils";
import { Component, useEffect, useState, onWillStart, useRef } from "@odoo/owl";
import { pick } from "@web/core/utils/objects";
import wUtils from "@website/js/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class BuilderUrlMultiPicker extends Component {
    static template = "website.BuilderUrlMultiPicker";
    static props = {
        ...basicContainerBuilderComponentProps,
        ...textInputBasePassthroughProps,
    };
    static components = {
        BuilderComponent,
        BuilderTextInputBase,
    };

    setup() {
        useBuilderComponent();
        this.inputRef = useRef("inputRef");
        this.editingEl = this.env.getEditingElement();
        this.state = useState({ value: "" });
        this.selection = useState([]);

        onWillStart(() => {
            const data = this.editingEl.dataset[this.env.weContext.dataAttributeAction];
            if (data) {
                this.selection = JSON.parse(data) || [];
            }
        })

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
                            this.select();
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

    unselect(id) {
        this.selection = this.selection.filter((item) => item.id !== id);
        this.editingEl.dataset[this.env.weContext.dataAttributeAction] = JSON.stringify(this.selection);
    }

    select() {
        const item = {
            id: this.inputRef.el.value,
            display_name: this.inputRef.el.value,
        }
        if (this.selection.find(selectionItem => selectionItem.id === item.id)) {
            return;
        }
        this.selection.push(item);
        this.state.value = "";
        this.editingEl.dataset[this.env.weContext.dataAttributeAction] = JSON.stringify(this.selection);
    }

    onInput() {
        this.state.value = this.inputRef.el.value;
    }
}

class UrlMultiPickerPlugin extends Plugin {
    static id = "urlMultiPickerPlugin";

    resources = {
        builder_components: {
            BuilderUrlMultiPicker,
        },
    };
}

registry.category("website-plugins").add(UrlMultiPickerPlugin.id, UrlMultiPickerPlugin);
