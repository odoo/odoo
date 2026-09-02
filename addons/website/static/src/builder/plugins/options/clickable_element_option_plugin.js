import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { setHrefUrl } from "@html_builder/plugins/utils";

export const CLICKABLE_LINK_SELECTOR = ":scope > a.stretched-link, :scope > a.slide-link";

function getClickableLink(editingElement) {
    return editingElement.querySelector(CLICKABLE_LINK_SELECTOR);
}

export class ClickableElementOptionPlugin extends Plugin {
    static id = "clickableElementOptionPlugin";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SetElementClickableAction,
            SetElementAnchorUrlAction,
        },
        clean_for_save_processors: this.cleanForSave.bind(this),
        is_empty_link_legit_predicates: (linkEl) => {
            if (linkEl.matches("a.stretched-link[href], .carousel-item > a.slide-link[href]")) {
                return true;
            }
        },
    };

    /**
     * @param {HTMLElement} root
     */
    cleanForSave(root) {
        for (const slideEl of root.querySelectorAll(".carousel-item.clickable-slide")) {
            slideEl.classList.remove("clickable-slide");
        }
        return root;
    }
}

class SetElementClickableAction extends BuilderAction {
    static id = "setElementClickable";
    apply({ editingElement }) {
        const linkEl = getClickableLink(editingElement);
        if (linkEl) {
            return;
        }
        const anchorEl = document.createElement("a");
        anchorEl.classList.add("stretched-link");
        editingElement.prepend(anchorEl);
    }
    clean({ editingElement }) {
        getClickableLink(editingElement)?.remove();
    }
    isApplied({ editingElement }) {
        return !!getClickableLink(editingElement);
    }
}

class SetElementAnchorUrlAction extends BuilderAction {
    static id = "setElementAnchorUrl";
    apply({ editingElement, value }) {
        const linkEl = getClickableLink(editingElement);
        if (linkEl) {
            setHrefUrl(linkEl, value);
        }
    }
    getValue({ editingElement }) {
        const linkEl = getClickableLink(editingElement);
        return linkEl?.getAttribute("href") || "";
    }
}

registry
    .category("website-plugins")
    .add(ClickableElementOptionPlugin.id, ClickableElementOptionPlugin);
