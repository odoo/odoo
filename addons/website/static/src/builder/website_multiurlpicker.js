import { Plugin } from "@html_editor/plugin";
import { useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import wUtils from "@website/js/utils";
import { BuilderMultiUrlPicker } from "@html_builder/core/building_blocks/builder_multiurlpicker";

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
     * Handles the selection of a URL from the input field.
     *
     * @returns {void}
     */
    select() {
        const url = this.inputRef.el.value;
        const selectedUrls = this.urls;
        this.inputRef.el.value = ""; // clear the input

        if (!url || selectedUrls.includes(url)) {
            return;
        }

        selectedUrls.push(url);
        this.commit(selectedUrls);
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
