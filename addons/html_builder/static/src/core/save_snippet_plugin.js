import { escapeTextNodes } from "@html_builder/utils/escaping";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { BLOCKQUOTE_PARENT_HANDLERS } from "@html_builder/core/utils";

/**
 * @typedef {CSSSelector[]} submit_button_selectors
 * CSS selectors matching different kinds of submit buttons.
 */

export class SaveSnippetPlugin extends Plugin {
    static id = "saveSnippet";
    /** @type {import("plugins").BuilderResources} */
    resources = {
        get_options_container_top_buttons: withSequence(
            1,
            this.getOptionsContainerTopButtons.bind(this)
        ),
    };

    setup() {
        this.savableSelector = `[data-snippet], a.btn, ${BLOCKQUOTE_PARENT_HANDLERS}`;
        this.unsavableSelector = [
            ".o_no_save",
            ...this.getResource("submit_button_selectors"),
        ].join(", ");
    }

    /**
     * Checks if the element can be saved as a custom snippet.
     *
     * @param {HTMLElement} el
     * @returns {boolean}
     */
    isSavable(el) {
        return el.matches(this.savableSelector) && !el.matches(this.unsavableSelector);
    }

    getOptionsContainerTopButtons(el) {
        if (!this.isSavable(el)) {
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
        // When saving a parent handler, save the child snippet instead
        if (el.matches(BLOCKQUOTE_PARENT_HANDLERS)) {
            const childBlockquote = el.querySelector(".s_blockquote");
            if (childBlockquote) {
                el = childBlockquote;
            }
        }
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
            if (this.delegateTo("custom_snippets_notification_handlers", savedName)) {
                return;
            }
            const message = _t(
                "Saved as %s. Find it in your snippets.",
                markup`<strong>${savedName}</strong>`
            );
            this.services.notification.add(message, {
                type: "success",
                autocloseDelay: 5000,
            });
        }
    }
}
