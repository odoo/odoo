import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class MassMailingIconSnippetOptionPlugin extends Plugin {
    static id = "mass_mailing.iconSnippetOption";
    static dependencies = ["icon", "dom"];
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    async onSnippetDropped({ snippetEl }) {
        if (!snippetEl.matches("p:has(> .s_icon)")) {
            return;
        }
        const selectedIconEl = await this.dependencies.icon.pickIcon({
            target: snippetEl,
            label: _t("Insert an icon"),
        });
        if (!selectedIconEl) {
            return true;
        }
        snippetEl.insertAdjacentElement("afterend", selectedIconEl);
        snippetEl.remove();
        this.dependencies.dom.wrapInlinesInBlocks(selectedIconEl.parentElement);
        return false;
    }
}

registry
    .category("mass_mailing-builder-plugins")
    .add(MassMailingIconSnippetOptionPlugin.id, MassMailingIconSnippetOptionPlugin);
