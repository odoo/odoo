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
    static dependencies = ["disableSnippets"];

    /** @type {import("plugins").BuilderResources} */
    resources = {
        options_container_top_buttons_providers: withSequence(
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
                class: "oi oi-fw oe_snippet_save o_we_hover_warning btn o-hb-btn btn-global-color-hover",
                icon: "save",
                title: _t("Save this block to use it elsewhere"),
                handler: this.saveSnippet.bind(this),
            },
        ];
    }

    async saveSnippet(el) {
        // When saving a parent handler, save the child snippet instead
        if (el.matches(BLOCKQUOTE_PARENT_HANDLERS)) {
            const childBlockquote = el.querySelector(".s_blockquote");
            if (childBlockquote) {
                el = childBlockquote;
            }
        }
        const savedName = await this.config.saveSnippet(el, async (el) => {
            await Promise.all(this.trigger("on_will_save_handlers", el));
            try {
                const cloneEl = el.cloneNode(true);
                const cleanedEl = this.processThrough("clean_for_save_processors", cloneEl, {
                    saveSnippet: true,
                });
                escapeTextNodes(cleanedEl);
                return cleanedEl;
            } finally {
                this.trigger("on_saved_handlers", el);
            }
        });
        this.dependencies.disableSnippets.disableUndroppableSnippets();
        if (savedName) {
            if (this.delegateTo("custom_snippets_notification_overrides", savedName)) {
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
