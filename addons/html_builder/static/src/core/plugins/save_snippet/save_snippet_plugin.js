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
                class: "fa fa-fw fa-save oe_snippet_save o_we_hover_warning btn btn-outline-warning",
                title: _t("Save this block to use it elsewhere"),
                handler: this.saveSnippet.bind(this),
            },
        ];
    }

    async saveSnippet(el) {
        const cleanForSaveHandlers = this.getResource("clean_for_save_handlers");
        const savedName = await this.config.saveSnippet(el, cleanForSaveHandlers);
        if (savedName) {
            const message = markup(
                _t(
                    "Your custom snippet was successfully saved as <strong>%s</strong>. Find it in your snippets collection.",
                    savedName
                )
            );
            this.services.notification.add(message, {
                type: "success",
                autocloseDelay: 5000,
            });
        }
    }
}
