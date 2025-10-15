import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

export class PopupVisibilityPlugin extends Plugin {
    static id = "popupVisibilityPlugin";
    static dependencies = ["visibility", "domObserver", "domReferenceMap"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        invisible_items: {
            selector: ".s_popup",
            target: ".modal",
            toggle: this.toggleModal.bind(this),
            showAfterClone: false,
        },
        on_snippet_dropped_handlers: ({ snippetEl }) => {
            // BS Modal won't ever hide when calling `hide` if `show` has not
            // been called before. So we call `show` (regardless of visibility)
            const modalEl = snippetEl.querySelector(".s_popup:scope > .modal");
            if (modalEl) {
                this.window.Modal.getOrCreateInstance(modalEl).show();
                const { hide, reset } = this.getHideOrResetScrollbarCallbacks(snippetEl);
                this.dependencies.domObserver.stageCustomMutation({ apply: hide, revert: reset });
            }
        },
        on_cloned_handlers: ({ cloneEl }) => {
            // BS Modal won't ever hide when calling `hide` if `show` has not
            // been called before. So we force hide the clone, and the original
            // element stays visible
            const modalEl = cloneEl.querySelector(".s_popup:scope > .modal");
            if (modalEl) {
                this.dependencies.domObserver.ignore(() => modalEl.classList.remove("show"));
                this.window.Modal.getOrCreateInstance(modalEl)._hideModal();
            }
        },
        on_will_remove_handlers: (el) => {
            if (el.matches(".s_popup")) {
                const { hide, reset } = this.getHideOrResetScrollbarCallbacks(el);
                this.dependencies.domObserver.applyCustomMutation({ apply: reset, revert: hide });
            }
        },
        scroll_destination_processors: (targetEl) =>
            targetEl.querySelector(".s_popup:scope > .modal") ?? targetEl,
        clean_for_save_processors: this.cleanForSave.bind(this),
        on_target_revealed_handlers: this.hidePopupsWithoutTarget.bind(this),
        attributes_mutation_value_processors: (value, { mutation }) => {
            const { nodeId, attributeName } = mutation;
            // On hide/show of the popup, the `style` attribute of the modal in
            // the popup is changed. This also happens with the option
            // "Backdrop" on the popup. When reverting/re-applying commits that
            // are supposed to change the option, we do not want to also change
            // whether the popup is hidden of not. Here, we keep the `display`
            // property in the `style` attribute unchanged when the history
            // revert/re-apply a commit that modified it.
            if (attributeName === "style") {
                const target = this.dependencies.domReferenceMap.getNodeById(nodeId);
                if (target.matches(".s_popup > .modal")) {
                    const re = /display: .*?;/;
                    const currentDisplay = target.attributes.style?.value.match(re)?.[0] ?? "";
                    return re.test(value)
                        ? value.replace(re, currentDisplay)
                        : value + currentDisplay;
                }
            }
            return value;
        },
        is_move_neighbor_predicates: (el) => (el.matches(".s_popup") ? false : undefined),
    };

    setup() {
        this.addDomListener(this.editable, "click", (ev) => {
            // Note: links are excluded here so that internal modal buttons do
            // not close the popup as we want to allow edition of those buttons.
            if (ev.target.matches(".s_popup .js_close_popup:not(a, .btn)")) {
                ev.stopPropagation();
                this.toggleModal(ev.target.closest(".s_popup"), false);
            }
        });
        const invalidateVisibility = this.dependencies.visibility.invalidateVisibility;
        this.addDomListener(this.editable, "shown.bs.modal", invalidateVisibility);
        this.addDomListener(this.editable, "hidden.bs.modal", invalidateVisibility);
        const domObserver = this.dependencies.domObserver;
        this.unpatchModal = this.window.Modal // null in tests without loadAssetsFrontendJS
            ? patch(this.window.Modal.prototype, {
                  _hideModal() {
                      return domObserver.ignore(() => super._hideModal());
                  },
                  show() {
                      return domObserver.ignore(() => super.show());
                  },
                  hide() {
                      return domObserver.ignore(() => super.hide());
                  },
              })
            : () => {};
    }

    destroy() {
        super.destroy();
        this.unpatchModal();
    }

    toggleModal(targetEl, show) {
        const modalEl = targetEl.querySelector(".modal");
        const modalInstance = this.window.Modal.getOrCreateInstance(modalEl);
        modalEl.dispatchEvent(new Event("transitionend"));
        // Ensures Bootstrap events are triggered even if the popup is
        // still transitioning.
        modalInstance._isTransitioning = false;
        if (show) {
            modalInstance.show();
        } else {
            modalInstance.hide();
        }
    }

    cleanForSave(rootEl) {
        // Do not hide a popup if it is saved as a custom snippet
        // (otherwise it appears empty in the snippet dialog)
        if (rootEl.matches(".s_popup")) {
            return rootEl;
        }
        for (const modalEl of rootEl.querySelectorAll(".s_popup .modal.show")) {
            // Do not call .hide() directly, because it is queued whereas
            // .dispose() is not.
            modalEl.classList.remove("show");
            const modal = this.window.Modal.getOrCreateInstance(modalEl);
            modal._hideModal();
            modal.dispose();
        }
        return rootEl;
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
                this.toggleModal(popupEl, false);
            }
        }
    }

    /**
     * The BS Modal hides the scrollbar when shown and reset it when hidden.
     * But when the builder inserts or removes a shown modal, it must handle
     * the scrollbar state. This helpers returns callbacks to do that.
     *
     * @param {HTMLElement} popupEl
     * @returns {{hide: () => void, reset: () => void}}
     */
    getHideOrResetScrollbarCallbacks(popupEl) {
        const [reset, hide] = ["reset", "hide"].map((methodName) => () => {
            if (popupEl.matches(".s_popup:has(.modal.show)")) {
                new this.window.Scrollbar()[methodName]();
            }
        });
        return { hide, reset };
    }
}

registry.category("website-plugins").add(PopupVisibilityPlugin.id, PopupVisibilityPlugin);
registry.category("translation-plugins").add(PopupVisibilityPlugin.id, PopupVisibilityPlugin);
