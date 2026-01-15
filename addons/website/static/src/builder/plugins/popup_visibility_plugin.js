import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

/**
 * @typedef { Object } PopupVisibilityShared
 * @property { PopupVisibilityPlugin['onTargetHide'] } onTargetHide
 * @property { PopupVisibilityPlugin['onTargetShow'] } onTargetShow
 */

export class PopupVisibilityPlugin extends Plugin {
    static id = "popupVisibilityPlugin";
    static dependencies = ["visibility", "history"];
    static shared = ["onTargetShow", "onTargetHide"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        target_show: this.onTargetShow.bind(this),
        target_hide: this.onTargetHide.bind(this),
        clean_for_save_handlers: this.cleanForSave.bind(this),
        on_restore_containers_handlers: this.hidePopupsWithoutTarget.bind(this),
        on_reveal_target_handlers: this.hidePopupsWithoutTarget.bind(this),
    };

    setup() {
        this.addDomListener(this.editable, "click", (ev) => {
            // Note: links are excluded here so that internal modal buttons do
            // not close the popup as we want to allow edition of those buttons.
            if (ev.target.matches(".s_popup .js_close_popup:not(a, .btn)")) {
                ev.stopPropagation();
                const popupEl = ev.target.closest(".s_popup");
                this.dependencies.visibility.hideElement(popupEl);
            }
        });
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

    onTargetShow(targetEl) {
        // Check if the popup is within the editable, because it is cloned on
        // save (see save plugin) and Bootstrap moves it if it is not within the
        // document (see Bootstrap Modal's _showElement).
        if (targetEl.matches(".s_popup") && this.editable.contains(targetEl)) {
            this.window.Modal.getOrCreateInstance(targetEl.querySelector(".modal")).show();
        }
    }

    onTargetHide(targetEl, isCleaning) {
        // Do not use Bootstrap to close the popup, as we are cleaning a
        // clone of it. Instead, hide it manually (see `cleanForSave`).
        if (targetEl.matches(".s_popup") && !isCleaning) {
            this.window.Modal.getOrCreateInstance(targetEl.querySelector(".modal")).hide();
        }
    }

    cleanForSave({ root: rootEl }) {
        // Hide the popups manually, as we cannot rely on the `onTargetHide`
        // flow since the cleaned popup is a clone and is not in the DOM.
        for (const modalEl of rootEl.querySelectorAll(".s_popup .modal.show")) {
            modalEl.parentElement.dataset.invisible = "1";
            // Do not call .hide() directly, because it is queued whereas
            // .dispose() is not.
            modalEl.classList.remove("show");
            this.window.Modal.getOrCreateInstance(modalEl)._hideModal();
            this.window.Modal.getInstance(modalEl).dispose();
        }
    }

    /**
     * Hides all the open popups that do not contain the given target element.
     *
     * @param {HTMLElement} targetEl the element
     */
    hidePopupsWithoutTarget(targetEl) {
        const openPopupEls = this.editable.querySelectorAll(".s_popup:not([data-invisible='1']");
        if (!openPopupEls.length) {
            return;
        }

        for (const popupEl of openPopupEls) {
            if (!popupEl.contains(targetEl)) {
                this.dependencies.visibility.toggleTargetVisibility(popupEl, false);
            }
        }
        this.config.updateInvisibleElementsPanel();
    }
}

registry.category("website-plugins").add(PopupVisibilityPlugin.id, PopupVisibilityPlugin);
