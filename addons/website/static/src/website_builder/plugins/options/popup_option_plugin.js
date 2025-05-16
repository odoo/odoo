import { SNIPPET_SPECIFIC, SNIPPET_SPECIFIC_END } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { getElementsWithOption } from "@html_builder/utils/utils";
import { withSequence } from "@html_editor/utils/resource";

export const POPUP = SNIPPET_SPECIFIC;
export const COOKIES_BAR = SNIPPET_SPECIFIC_END;

class PopupOptionPlugin extends Plugin {
    static id = "PopupOption";
    static dependencies = ["anchor", "visibility", "history", "popupVisibilityPlugin"];

    resources = {
        builder_options: [
            withSequence(POPUP, {
                template: "html_builder.PopupOption",
                selector: ".s_popup",
                exclude: "#website_cookies_bar",
                applyTo: ".modal",
            }),
            withSequence(COOKIES_BAR, {
                template: "html_builder.PopupCookiesOption",
                selector: ".s_popup#website_cookies_bar",
                applyTo: ".modal",
            }),
        ],
        dropzone_selector: {
            selector: ".s_popup",
            exclude: "#website_cookies_bar",
            dropIn: ":not(p).oe_structure:not(.oe_structure_solo):not([data-snippet] *), :not(.o_mega_menu):not(p)[data-oe-type=html]:not([data-snippet] *)",
        },
        builder_actions: this.getActions(),
        on_cloned_handlers: this.onCloned.bind(this),
        on_remove_handlers: this.onRemove.bind(this),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    getActions() {
        return {
            // Moves the snippet in #o_shared_blocks to be common to all pages
            // or inside the first editable oe_structure in the main to be on
            // current page only.
            moveBlock: {
                isApplied: ({ editingElement, value }) =>
                    editingElement.closest("#o_shared_blocks")
                        ? value === "allPages"
                        : value === "currentPage",
                apply: ({ editingElement, value }) => {
                    const selector =
                        value === "allPages" ? "#o_shared_blocks" : "main .oe_structure.o_editable";
                    const whereEl = this.editable.querySelector(selector);
                    const popupEl = editingElement.closest(".s_popup");
                    whereEl.insertAdjacentElement("afterbegin", popupEl);
                },
            },
            setBackdrop: {
                isApplied: ({ editingElement }) => {
                    const hasBackdropColor =
                        editingElement.style.getPropertyValue("background-color").trim() ===
                        "var(--black-50)";
                    const hasNoBackdropClass =
                        editingElement.classList.contains("s_popup_no_backdrop");
                    return hasBackdropColor && !hasNoBackdropClass;
                },
                apply: ({ editingElement }) => {
                    editingElement.classList.remove("s_popup_no_backdrop");
                    editingElement.style.setProperty(
                        "background-color",
                        "var(--black-50)",
                        "important"
                    );
                },
                clean: ({ editingElement }) => {
                    editingElement.classList.add("s_popup_no_backdrop");
                    editingElement.style.removeProperty("background-color");
                },
            },
            copyAnchor: {
                apply: ({ editingElement }) => {
                    this.dependencies.anchor.createOrEditAnchorLink(
                        editingElement.closest(".s_popup")
                    );
                },
            },
            setPopupDelay: {
                apply: ({ editingElement, value }) => {
                    editingElement.dataset.showAfter = value * 1000;
                },
                getValue: ({ editingElement }) => editingElement.dataset.showAfter / 1000,
            },
        };
    }

    onCloned({ cloneEl }) {
        if (cloneEl.matches(".s_popup")) {
            this.assignUniqueID(cloneEl);
        }
    }

    onRemove(el) {
        this.dependencies.popupVisibilityPlugin.onTargetHide(el);
        this.dependencies.history.addCustomMutation({
            apply: () => {},
            revert: () => {
                this.dependencies.popupVisibilityPlugin.onTargetShow(el);
            },
        });
    }

    onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_popup")) {
            this.assignUniqueID(snippetEl);
            this.dependencies.history.addCustomMutation({
                apply: () => {
                    this.dependencies.popupVisibilityPlugin.onTargetShow(snippetEl);
                },
                revert: () => {
                    this.dependencies.popupVisibilityPlugin.onTargetHide(snippetEl);
                },
            });
        }
        const droppedEls = getElementsWithOption(snippetEl, ".s_popup");
        droppedEls.forEach((droppedEl) =>
            this.dependencies.visibility.toggleTargetVisibility(droppedEl, true, true)
        );
    }

    assignUniqueID(editingElement) {
        editingElement.closest(".s_popup").id = `sPopup${Date.now()}`;
    }
}

registry.category("website-plugins").add(PopupOptionPlugin.id, PopupOptionPlugin);
