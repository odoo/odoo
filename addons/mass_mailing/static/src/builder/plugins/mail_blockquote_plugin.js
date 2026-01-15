import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class AlertOptionPlugin extends Plugin {
    static id = "mass_mailing.MailBlockquotePlugin";

    resources = {
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    cleanForSave({ root }) {
        for (const quote of root.querySelectorAll("blockquote")) {
            quote.dataset.oMailQuoteNode = "1";
            quote.dataset.oMailQuote = "1";
        }
    }
}

registry.category("mass_mailing-plugins").add(AlertOptionPlugin.id, AlertOptionPlugin);
