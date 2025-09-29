import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { BLOCKQUOTE_PARENT_HANDLERS } from "@html_builder/core/utils";

const savableSelector = `[data-snippet], a.btn, ${BLOCKQUOTE_PARENT_HANDLERS}`;
// TODO `so_submit_button_selector` ?
const savableExclude =
    ".o_no_save, .s_donation_donate_btn, .s_website_form_send, .js_subscribe_btn";

// Checks if the element can be saved as a custom snippet.
function isSavable(el) {
    return el.matches(savableSelector) && !el.matches(savableExclude);
}

export class SaveSnippetPlugin extends Plugin {
    static id = "saveSnippet";
    static dependencies = ["savePlugin"];
    /** @type {import("plugins").BuilderResources} */
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

    async saveSnippet(el) {
        // When saving a parent handler, save the child snippet instead
        if (el.matches(BLOCKQUOTE_PARENT_HANDLERS)) {
            const childBlockquote = el.querySelector(".s_blockquote");
            if (childBlockquote) {
                el = childBlockquote;
            }
        }
        const savedName = await this.config.saveSnippet(el, async (el) => {
            await Promise.all(
                this.getResource("before_save_handlers").map((handler) => handler(el))
            );
            try {
                return this.dependencies.savePlugin.prepareElementForSave(el);
            } finally {
                this.getResource("after_save_handlers").forEach((handler) => handler(el));
            }
        });
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
