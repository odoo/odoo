import { escapeTextNodes } from "@html_builder/utils/escaping";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

const savableSelector = "[data-snippet], a.btn";
// TODO `so_submit_button_selector` ?
const savableExclude = ".o_no_save, .s_donation_donate_btn, .s_website_form_send";

// Checks if the element can be saved as a custom snippet.
function isSavable(el) {
    return el.matches(savableSelector) && !el.matches(savableExclude);
}

export class SaveSnippetPlugin extends Plugin {
    static id = "saveSnippet";
    resources = {
        get_options_container_top_buttons: withSequence(
            1,
            this.getOptionsContainerTopButtons.bind(this)
        ),
    };

    getOptionsContainerTopButtons(el) {
        if (!isSavable(el)) {
            return [];
        }

        return [
            {
                class: "fa fa-fw fa-save oe_snippet_save o_we_hover_warning btn o-hb-btn btn-global-color-hover",
                title: _t("Save this block to use it elsewhere"),
                handler: this.saveSnippet.bind(this),
            },
        ];
    }

    /**
     * Execute the `before_save_handlers` on {@link snippetEl},
     * then execute {@link callback}, and finally execute the
     * `after_save_handlers` on {@link snippetEl}.
     * This is used, for example, to stop the interactions before cloning a
     * snippet, and restarting them after cloning it.
     *
     * @param {HTMLElement} snippetEl
     * @param {Function} callback
     */
    async wrapWithBeforeAfterSaveHandlers(snippetEl, callback) {
        await Promise.all(
            this.getResource("before_save_handlers").map((handler) => handler(snippetEl))
        );
        let node;
        try {
            node = callback();
        } finally {
            this.getResource("after_save_handlers").forEach((handler) => handler(snippetEl));
        }
        return node;
    }

    async saveSnippet(el) {
        const cleanForSaveHandlers = [
            ...this.getResource("clean_for_save_handlers"),
            ({ root }) => escapeTextNodes(root),
        ];
        const savedName = await this.config.saveSnippet(
            el,
            cleanForSaveHandlers,
            this.wrapWithBeforeAfterSaveHandlers.bind(this)
        );
        if (savedName) {
            const message = _t(
                "Your custom snippet was successfully saved as %s. Find it in your snippets collection.",
                markup`<strong>${savedName}</strong>`
            );
            this.services.notification.add(message, {
                type: "success",
                autocloseDelay: 5000,
            });
        }
    }
}
