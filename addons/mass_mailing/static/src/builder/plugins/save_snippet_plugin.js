import { Plugin } from "@html_editor/plugin";
import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class SaveSnippetPlugin extends Plugin {
    static id = "mass_mailing.SaveSnippetPlugin";
    resources = {
        custom_snippets_notification_handlers: this.handleCustomSnippetNotification.bind(this),
    };

    handleCustomSnippetNotification(savedName) {
        if (this.config.getRecordInfo().resModel !== "mailing.mailing") {
            return false;
        }
        const message = _t(
            "Your custom snippet was successfully saved as %s. Find it in your custom snippets collection.",
            markup`<strong>${savedName}</strong>`
        );
        this.closeNotification = this.services.notification.add(message, {
            type: "success",
            autocloseDelay: 10000,
        });
        return true;
    }
}
registry.category("mass_mailing-plugins").add(SaveSnippetPlugin.id, SaveSnippetPlugin);
