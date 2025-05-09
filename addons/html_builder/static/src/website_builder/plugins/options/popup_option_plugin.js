import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { getElementsWithOption } from "@html_builder/utils/utils";
import { withSequence } from "@html_editor/utils/resource";
import { SNIPPET_SPECIFIC_END } from "@html_builder/website_builder/option_sequence";
export const COOKIES_BAR = SNIPPET_SPECIFIC_END;

class PopupOptionPlugin extends Plugin {
    static id = "PopupOption";
    static dependencies = ["anchor", "visibility", "history"];

    resources = {
        builder_options: [
            {
                template: "html_builder.PopupOption",
                selector: ".s_popup",
                exclude: "#website_cookies_bar",
                applyTo: ".modal",
            },
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
        target_show: this.onTargetShow.bind(this),
        target_hide: this.onTargetHide.bind(this),
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    setup() {
        this.addDomListener(this.editable, "click", (ev) => {
            // Note: links are excluded here so that internal modal buttons do
            // not close the popup as we want to allow edition of those buttons.
            if (ev.target.matches(".s_popup .js_close_popup:not(a, .btn)")) {
                ev.stopPropagation();
                const popupEl = ev.target.closest(".s_popup");
                this.onTargetHide(popupEl);
                this.dependencies.visibility.onOptionVisibilityUpdate(popupEl, false);
            }
        });
    }

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
        this.onTargetHide(el);
        this.dependencies.history.addCustomMutation({
            apply: () => {},
            revert: () => {
                this.onTargetShow(el);
            },
        });
    }

    onSnippetDropped({ snippetEl }) {
        if (snippetEl.matches(".s_popup")) {
            this.assignUniqueID(snippetEl);
            this.dependencies.history.addCustomMutation({
                apply: () => {
                    this.onTargetShow(snippetEl);
                },
                revert: () => {
                    this.onTargetHide(snippetEl);
                },
            });
        }
        const droppedEls = getElementsWithOption(snippetEl, ".s_popup");
        droppedEls.forEach((droppedEl) =>
            this.dependencies.visibility.toggleTargetVisibility(droppedEl, true, true)
        );
    }

    onTargetShow(target) {
        // Check if the popup is within the editable, because it is cloned on
        // save (see save plugin) and Bootstrap moves it if it is not within the
        // document (see Bootstrap Modal's _showElement).
        if (target.matches(".s_popup") && this.editable.contains(target)) {
            this.window.Modal.getOrCreateInstance(target.querySelector(".modal")).show();
        }
    }

    onTargetHide(target) {
        if (target.matches(".s_popup")) {
            this.window.Modal.getOrCreateInstance(target.querySelector(".modal")).hide();
        }
    }

    cleanForSave({ root }) {
        for (const modalEl of root.querySelectorAll(".s_popup .modal.show")) {
            modalEl.parentElement.dataset.invisible = "1";
            // Do not call .hide() directly, because it is queued whereas
            // .dispose() is not.
            modalEl.classList.remove("show");
            this.window.Modal.getOrCreateInstance(modalEl)._hideModal();
            this.window.Modal.getInstance(modalEl).dispose();
        }
    }

    assignUniqueID(editingElement) {
        editingElement.closest(".s_popup").id = `sPopup${Date.now()}`;
    }
}

registry.category("website-plugins").add(PopupOptionPlugin.id, PopupOptionPlugin);
