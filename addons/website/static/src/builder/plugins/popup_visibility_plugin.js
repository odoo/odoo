import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

export class PopupVisibilityPlugin extends Plugin {
    static id = "popupVisibilityPlugin";
    static dependencies = ["visibility", "history"];

    resources = {
        invisible_items: {
            selector: ".s_popup",
            target: ".modal",
            toggle: (el, show) => {
                const modal = this.window.Modal.getOrCreateInstance(el.querySelector(".modal"));
                show ? modal.show() : modal.hide();
            },
        },
        clean_for_save_handlers: this.cleanForSave.bind(this),
        reveal_target_handlers: this.hidePopupsWithoutTarget.bind(this),
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
            if (!popupEl.contains(targetEl) && !targetEl.contains(popupEl)) {
                this.window.Modal.getOrCreateInstance(popupEl.querySelector(".modal")).hide();
            }
        }
    }
}

registry.category("website-plugins").add(PopupVisibilityPlugin.id, PopupVisibilityPlugin);
