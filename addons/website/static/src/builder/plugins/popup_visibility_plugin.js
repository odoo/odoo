/** @odoo-module native */
import { getBootstrapComponent } from "@html_builder/core/bootstrap_realm";
import { Plugin } from "@html_editor/plugin";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const log = makeLogger("website.builder.plugin.popup_visibility_plugin");

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
            if (ev.target.matches(".s_popup .js_close_popup:not(a, .btn)")) {
                ev.stopPropagation();
                const popupEl = ev.target.closest(".s_popup");
                log.logic("close popup button clicked: hiding popup", () => ({
                    id: popupEl?.id,
                }));
                this.dependencies.visibility.hideElement(popupEl);
            }
        });
        const history = this.dependencies.history;
        const Modal = this.getModal();
        log.lifecycle("setup", () => ({ patchModal: !!Modal }));
        this.unpatchModal = Modal
            ? patch(Modal.prototype, {
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

    /**
     * @returns {Function|undefined}
     */
    getModal() {
        return getBootstrapComponent(this.window, "Modal");
    }

    destroy() {
        log.lifecycle("destroy");
        super.destroy();
        this.unpatchModal();
    }

    /**
     * @param {HTMLElement} targetEl
     * @returns {HTMLElement|null}
     */
    getModalEl(targetEl) {
        return targetEl.matches(".s_popup") ? targetEl.querySelector(".modal") : null;
    }

    onTargetShow(targetEl) {
        if (!this.editable.contains(targetEl)) {
            log.logic("onTargetShow skip: target outside editable");
            return;
        }
        const modalEl = this.getModalEl(targetEl);
        const Modal = this.getModal();
        if (modalEl && Modal) {
            log.pipeline("onTargetShow show popup modal", () => ({ id: targetEl.id }));
            this.settleModal(Modal.getOrCreateInstance(modalEl), true);
        }
    }

    /**
     * Bootstrap silently drops a show() or hide() that arrives while the
     * opposite transition is still running (the eye toggled twice within a
     * fade), leaving the popup in the state the panel does not claim. The
     * call is replayed once that transition ends.
     *
     * @param {import("bootstrap").Modal} modal
     * @param {boolean} shown the state the popup must end in
     */
    settleModal(modal, shown) {
        if (modal._isTransitioning && modal._isShown !== shown) {
            const event = shown ? "hidden.bs.modal" : "shown.bs.modal";
            log.logic("settleModal: transition in flight, replaying after", () => ({
                event,
            }));
            const endWait = log.perf("settleModal wait", () => ({ event }));
            modal._element.addEventListener(
                event,
                () => {
                    endWait();
                    if (shown) {
                        modal.show();
                    } else {
                        modal.hide();
                    }
                },
                { once: true },
            );
            return;
        }
        if (shown) {
            modal.show();
        } else {
            modal.hide();
        }
    }

    onTargetHide(targetEl, isCleaning) {
        if (isCleaning) {
            log.logic("onTargetHide skip: cleaning");
            return;
        }
        const modalEl = this.getModalEl(targetEl);
        const Modal = this.getModal();
        if (modalEl && Modal) {
            log.pipeline("onTargetHide hide popup modal", () => ({ id: targetEl.id }));
            this.settleModal(Modal.getOrCreateInstance(modalEl), false);
        }
    }

    cleanForSave({ root: rootEl }) {
        const Modal = this.getModal();
        if (!Modal) {
            log.logic("cleanForSave skip: no bootstrap Modal");
            return;
        }
        log.pipeline("cleanForSave hide open popups", () => ({
            count: rootEl.querySelectorAll(".s_popup .modal.show").length,
        }));
        for (const modalEl of rootEl.querySelectorAll(".s_popup .modal.show")) {
            modalEl.parentElement.dataset.invisible = "1";
            modalEl.classList.remove("show");
            const modal = Modal.getOrCreateInstance(modalEl);
            modal._hideModal();
            modal.dispose();
        }
    }

    /**
     * @param {HTMLElement} targetEl
     */
    hidePopupsWithoutTarget(targetEl) {
        const openPopupEls = this.editable.querySelectorAll(
            ".s_popup:not([data-invisible='1'])",
        );
        if (!openPopupEls.length) {
            return;
        }

        log.pipeline("hidePopupsWithoutTarget", () => ({
            openPopups: openPopupEls.length,
        }));
        for (const popupEl of openPopupEls) {
            if (!popupEl.contains(targetEl)) {
                this.dependencies.visibility.toggleTargetVisibility(popupEl, false);
            }
        }
        this.config.updateInvisibleElementsPanel();
    }
}

registry
    .category("website-plugins")
    .add(PopupVisibilityPlugin.id, PopupVisibilityPlugin);
