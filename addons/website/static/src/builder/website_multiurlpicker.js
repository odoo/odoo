import { BuilderMultiUrlPicker } from "@html_builder/core/building_blocks/builder_multiurlpicker";
import { Plugin } from "@html_editor/plugin";
import { useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import wUtils from "@website/js/utils";

export class WebsiteMultiUrlPicker extends BuilderMultiUrlPicker {
    setup() {
        super.setup();

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
                        urlChosen: this.select.bind(this),
                    },
                    this.env
                );
                return () => unmountAutocompleteWithPages();
            },
            () => [this.inputRef.el]
        );
    }

    /**
     * @override
     */
    handleEnterKey(ev) {
        // It prevents double selection of URL when pressing Enter key
        // to select an URL from the autocomplete list.
        return;
    }
}

class MultiUrlPickerPlugin extends Plugin {
    static id = "multiUrlPickerPlugin";

    resources = {
        builder_components: {
            WebsiteMultiUrlPicker,
        },
    };
}

registry.category("website-plugins").add(MultiUrlPickerPlugin.id, MultiUrlPickerPlugin);
