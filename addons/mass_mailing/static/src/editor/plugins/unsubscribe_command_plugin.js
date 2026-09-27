import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { renderToElement } from "@web/core/utils/render";

export class UnsubscribeCommandPlugin extends Plugin {
    static id = "unsubscribeCommandPlugin";
    static dependencies = ["history", "dom"];
    resources = {
        user_commands: [
            {
                id: "insertUnsubscribeLink",
                title: _t("Unsubscribe Link"),
                description: _t("Insert an unsubscribe link"),
                icon: "link_off",
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
    };

    insertUnsubscribeLink() {
        const unsubscribeEl = renderToElement("mass_mailing.s_unsubscribe_link");
        this.dependencies.dom.insert(unsubscribeEl);
        this.dependencies.history.commit();
    }
}

registry
    .category("mass_mailing-plugins")
    .add(UnsubscribeCommandPlugin.id, UnsubscribeCommandPlugin);
registry
    .category("basic-editor-plugins")
    .add(UnsubscribeCommandPlugin.id, UnsubscribeCommandPlugin);
