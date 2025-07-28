import { SNIPPET_SPECIFIC, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { withSequence } from "@html_editor/utils/resource";
import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";

export const POPUP = SNIPPET_SPECIFIC;
export const COOKIES_BAR = SNIPPET_SPECIFIC_END;

export class PopupOption extends BaseOptionComponent {
    static template = "website.PopupOption";
    static selector = ".s_popup";
    static exclude = "#website_cookies_bar";
    static applyTo = ".modal";
}

export class PopupCookiesOption extends BaseOptionComponent {
    static template = "website.PopupCookiesOption";
    static selector = ".s_popup#website_cookies_bar";
    static applyTo = ".modal";
}

class PopupOptionPlugin extends Plugin {
    static id = "PopupOption";
    static dependencies = ["anchor", "visibility", "history", "popupVisibilityPlugin"];

    resources = {
        builder_options: [
            withSequence(POPUP, PopupOption),
            withSequence(COOKIES_BAR, PopupCookiesOption),
        ],
        dropzone_selector: {
            selector: ".s_popup",
            exclude: "#website_cookies_bar",
            dropIn: ":not(p).oe_structure:not(.oe_structure_solo):not([data-snippet] *), :not(.o_mega_menu):not(p)[data-oe-type=html]:not([data-snippet] *)",
        },
        builder_actions: {
            // Moves the snippet in #o_shared_blocks to be common to all pages
            // or inside the first editable oe_structure in the main to be on
            // current page only.
            MoveBlockAction,
            SetBackdropAction,
            CopyAnchorAction,
            SetPopupDelayAction,
        },
        on_cloned_handlers: this.onCloned.bind(this),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
        on_will_remove_handlers: this.onWillRemove.bind(this),
        no_parent_containers: ".s_popup",
    };

    onCloned({ cloneEl }) {
        if (cloneEl.matches(".s_popup")) {
            this.assignUniqueID(cloneEl);
        }
    }

    onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_popup")) {
            this.assignUniqueID(snippetEl);
            this.dependencies.history.addCustomMutation({
                apply: () => {
                    this.dependencies.visibility.toggleTargetVisibility(snippetEl, true);
                },
                revert: () => {
                    this.dependencies.visibility.toggleTargetVisibility(snippetEl, false);
                },
            });
        }
    }

    onWillRemove(el) {
        this.dependencies.visibility.toggleTargetVisibility(el, false);
        this.dependencies.history.addCustomMutation({
            apply: () => {
                this.dependencies.visibility.toggleTargetVisibility(el, false);
            },
            revert: () => {
                this.dependencies.visibility.toggleTargetVisibility(el, true);
            },
        });
    }

    assignUniqueID(editingElement) {
        editingElement.closest(".s_popup").id = `sPopup${Date.now()}`;
    }
}

// Moves the snippet in #o_shared_blocks to be common to all pages
// or inside the first editable oe_structure in the main to be on
// current page only.
export class MoveBlockAction extends BuilderAction {
    static id = "moveBlock";
    isApplied({ editingElement, value }) {
        return editingElement.closest("#o_shared_blocks")
            ? value === "allPages"
            : value === "currentPage";
    }
    apply({ editingElement, value }) {
        const selector =
            value === "allPages" ? "#o_shared_blocks" : "main .oe_structure.o_editable";
        const whereEl = this.editable.querySelector(selector);
        const popupEl = editingElement.closest(".s_popup");
        whereEl.insertAdjacentElement("afterbegin", popupEl);
    }
}
export class SetBackdropAction extends BuilderAction {
    static id = "setBackdrop";
    isApplied({ editingElement }) {
        const hasBackdropColor = !!editingElement.style.getPropertyValue("background-color").trim();
        const hasNoBackdropClass = editingElement.classList.contains("s_popup_no_backdrop");
        return hasBackdropColor && !hasNoBackdropClass;
    }
    apply({ editingElement }) {
        editingElement.classList.remove("s_popup_no_backdrop");
        editingElement.style.setProperty("background-color", "var(--black-50)", "important");
    }
    clean({ editingElement }) {
        editingElement.classList.add("s_popup_no_backdrop");
        editingElement.style.removeProperty("background-color");
    }
}
export class CopyAnchorAction extends BuilderAction {
    static id = "copyAnchor";
    static dependencies = ["anchor"];
    apply({ editingElement }) {
        this.dependencies.anchor.createOrEditAnchorLink(editingElement);
    }
}
export class SetPopupDelayAction extends BuilderAction {
    static id = "setPopupDelay";
    apply({ editingElement, value }) {
        editingElement.dataset.showAfter = value * 1000;
    }
    getValue({ editingElement }) {
        return editingElement.dataset.showAfter / 1000;
    }
}

registry.category("website-plugins").add(PopupOptionPlugin.id, PopupOptionPlugin);
