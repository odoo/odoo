import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class UnsubscribeCommandPlugin extends Plugin {
    static id = "unsubscribeCommandPlugin";
    static dependencies = ["selection", "history", "dom"];
    resources = {
        user_commands: [
            {
                id: "insertUnsubscribeLink",
                title: _t("Unsubscribe Link"),
                description: _t("Insert an unsubscribe link"),
                icon: "fa-chain-broken",
                run: this.insertUnsubscribeLink.bind(this),
                isAvailable: (selection) => isHtmlContentSupported(selection),
            },
        ],
        powerbox_items: [
            {
                categoryId: "navigation",
                commandId: "insertUnsubscribeLink",
            },
        ],
        on_mailing_model_updated_handlers: this.onMailingModelUpdated.bind(this),
    };

    insertUnsubscribeLink() {
        const snippet = this.config.snippetModel.getSnippetByName("snippet_content", "s_unsubscribe_link");
        const content = snippet.content.cloneNode(true);
        this.dependencies.dom.insert(content);
        this.dependencies.history.addStep();
    }

    setup() {
        this.onMailingModelUpdated();
    }

    /**
     * Hide unsubscribe links if the mailing targets employees
     */
    onMailingModelUpdated() {
        const unsubEls = this.editable.querySelectorAll(".o_layout a[href='/unsubscribe_from_list']");

        for (const el of unsubEls) {
            if (this.config.getRecordInfo?.().data.mailing_model_real == "hr.employee") {
                el.style.display = "none";
            } else if (el.style.display == "none") {
                el.style.display = null;
            }
        }
    }
}

registry.category("mass_mailing-plugins").add(UnsubscribeCommandPlugin.id, UnsubscribeCommandPlugin);
registry.category("basic-editor-plugins").add(UnsubscribeCommandPlugin.id, UnsubscribeCommandPlugin);
