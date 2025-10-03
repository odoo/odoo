import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

export class PopupVisibilityPlugin extends Plugin {
    static id = "popupVisibilityPlugin";
    static dependencies = ["visibility", "history"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        invisible_items: {
            selector: ".s_popup",
            target: ".modal",
            toggle: (el, show) => {
                const modal = this.window.Modal.getOrCreateInstance(el.querySelector(".modal"));
                show ? modal.show() : modal.hide();
            },
            noShowAfterClone: true,
        },
        on_snippet_dropped_handlers: ({ snippetEl }) => {
            // BS Modal won't ever hide when calling `hide` if `show` has not
            // been called before. So we call `show` (regardless of visibility)
            const modalEl = snippetEl.querySelector(".s_popup:scope > .modal");
            if (modalEl) {
                this.dependencies.history.addCustomMutation({
                    apply: () => this.hideScrollbarForVisiblePopup(snippetEl),
                    revert: () => {},
                });
                const modal = this.window.Modal.getOrCreateInstance(modalEl);
                modal.show();
                this.dependencies.history.applyCustomMutation({
                    apply: () => this.hidePopupsWithoutTarget(modalEl),
                    revert: () => this.resetScrollbarForVisiblePopup(snippetEl),
                });
            }
        },
        on_cloned_handlers: ({ cloneEl }) => {
            // BS Modal won't ever hide when calling `hide` if `show` has not
            // been called before. So we force hide the clone, and the original
            // element stays visible
            const modalEl = cloneEl.querySelector(".s_popup:scope > .modal");
            if (modalEl) {
                const modal = this.window.Modal.getOrCreateInstance(modalEl);
                this.dependencies.history.ignoreDOMMutations(() =>
                    modalEl.classList.remove("show")
                );
                modal._hideModal();
            }
        },
        on_will_remove_handlers: (el) => {
            if (el.matches(".s_popup")) {
                this.dependencies.history.applyCustomMutation({
                    apply: () => this.resetScrollbarForVisiblePopup(el),
                    revert: () => this.hideScrollbarForVisiblePopup(el),
                });
            }
        },
        reveal_target_destination_processors: (targetEl) =>
            targetEl.querySelector(".s_popup:scope > .modal") ?? targetEl,
        reveal_target_handlers: this.hidePopupsWithoutTarget.bind(this),
        clean_for_save_handlers: this.cleanForSave.bind(this),
    };

    setup() {
        this.addDomListener(this.editable, "click", (ev) => {
            // Note: links are excluded here so that internal modal buttons do
            // not close the popup as we want to allow edition of those buttons.
            if (ev.target.matches(".s_popup .js_close_popup:not(a, .btn)")) {
                ev.stopPropagation();
                const modalEl = ev.target.closest(".s_popup").querySelector(".modal");
                this.window.Modal.getOrCreateInstance(modalEl).hide();
            }
        });
        const invalidateVisibility = this.dependencies.visibility.invalidateVisibility;
        this.addDomListener(this.editable, "shown.bs.modal", invalidateVisibility);
        this.addDomListener(this.editable, "hidden.bs.modal", invalidateVisibility);
        const history = this.dependencies.history;
        this.unpatchModal = this.window.Modal // null in tests without loadAssetsFrontendJS
            ? patch(this.window.Modal.prototype, {
                  _hideModal() {
                      return history.ignoreDOMMutations(() => super._hideModal());
                  },
                  show() {
                      return history.ignoreDOMMutations(() => super.show());
                  },
                  hide() {
                      return history.ignoreDOMMutations(() => super.hide());
                  },
              })
            : () => {};
    }

    destroy() {
        super.destroy();
        this.unpatchModal();
    }

    cleanForSave({ root: rootEl }) {
        for (const modalEl of rootEl.querySelectorAll(".s_popup:not(:scope) > .modal.show")) {
            // Do not call .hide() directly, because it is queued whereas
            // .dispose() is not.
            modalEl.classList.remove("show");
            const modal = this.window.Modal.getOrCreateInstance(modalEl);
            modal._hideModal();
            modal.dispose();
        }
    }

    /**
     * Hides all the open popups that do not contain the given target element.
     *
     * @param {HTMLElement} targetEl the element
     */
    hidePopupsWithoutTarget(targetEl) {
        const openPopupEls = this.editable.querySelectorAll(".s_popup:has(> .modal.show)");
        for (const popupEl of openPopupEls) {
            if (!popupEl.contains(targetEl)) {
                this.window.Modal.getOrCreateInstance(popupEl.querySelector(".modal")).hide();
            }
        }
    }

    // BS Modal hide the scrollbar when shown and reset it when hidden.
    // When the modal is removed, we reset the scrollbar here (if it is shown)
    resetScrollbarForVisiblePopup(popupEl) {
        if (popupEl.matches(".s_popup:has(.modal.show)")) {
            new this.window.Scrollbar().reset();
        }
    }

    // BS Modal hide the scrollbar when shown and reset it when hidden.
    // When the modal is added without getting shown, we hide the scrollbar here
    hideScrollbarForVisiblePopup(popupEl) {
        if (popupEl.matches(".s_popup:has(.modal.show)")) {
            new this.window.Scrollbar().hide();
        }
    }
}

registry.category("website-plugins").add(PopupVisibilityPlugin.id, PopupVisibilityPlugin);
registry.category("translation-plugins").add(PopupVisibilityPlugin.id, PopupVisibilityPlugin);
