import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { setHrefUrl } from "@html_builder/plugins/utils";

export class ClickableCardOptionPlugin extends Plugin {
    static id = "clickableCardOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SetCardClickableAction,
            SetCardAnchorUrlAction,
        },
        is_empty_link_legit_predicates: (linkEl) => {
            if (linkEl.matches("a.stretched-link[href]")) {
                return true;
            }
        },
    };
}

class SetCardClickableAction extends BuilderAction {
    static id = "setCardClickable";
    apply({ editingElement }) {
        const anchorEl = document.createElement("a");
        anchorEl.classList.add("stretched-link");
        editingElement.prepend(anchorEl);
    }
    clean({ editingElement }) {
        editingElement.querySelector(":scope > a.stretched-link")?.remove();
    }
    isApplied({ editingElement }) {
        return !!editingElement.querySelector(":scope > a.stretched-link");
    }
}

class SetCardAnchorUrlAction extends BuilderAction {
    static id = "setCardAnchorUrl";
    apply({ editingElement, value }) {
        const linkEl = editingElement.querySelector(":scope > a.stretched-link");
        if (linkEl) {
            setHrefUrl(linkEl, value);
        }
    }
    getValue({ editingElement }) {
        const linkEl = editingElement.querySelector(":scope > a.stretched-link");
        return linkEl?.getAttribute("href") || "";
    }
}

registry.category("website-plugins").add(ClickableCardOptionPlugin.id, ClickableCardOptionPlugin);
