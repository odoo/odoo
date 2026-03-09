import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class EmptyMailingPlugin extends Plugin {
    static id = "EmptyMailing";
    static dependencies = [
        "baseContainer",
        "builderOptions",
        "disableSnippets",
        "history",
        "selection",
        "blockTab",
    ];

    setup() {
        this.addDomListener(this.editable, "click", this.onMailWrapperClick);
    }

    onMailWrapperClick(ev) {
        const wrapperId = ev.target.matches(".o_mail_wrapper_td.oe_empty") ? ev.target : null;
        if (!wrapperId) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();

        const snippet = this.config.snippetModel.getSnippetByName(
            "snippet_groups",
            "s_snippet_group"
        );
        this.dependencies.blockTab.onSnippetGroupClick(snippet, {});
    }
}

registry.category("mass_mailing-plugins").add(EmptyMailingPlugin.id, EmptyMailingPlugin);
