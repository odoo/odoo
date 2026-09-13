/** @odoo-module native */
import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { getTabableElements } from "@web/core/utils/dom/ui";
import { Modal } from "@web/libs/bootstrap";
import { Interaction } from "@web/public/interaction";
import { SIZES, utils as uiUtils } from "@web/ui/viewport";

const log = makeLogger("website.interaction.popup");

export class Popup extends Interaction {
    static selector = ".s_popup:not(#website_cookies_bar)";
    dynamicContent = {
        ".js_close_popup": {
            "t-on-click": this.onCloseClick,
        },
        ".btn-primary": {
            "t-on-click": this.onBtnPrimaryClick,
        },
        _root: {
            "t-on-hide.bs.modal": this.onHideModal,
            "t-on-shown.bs.modal": this.trapFocus,
        },
        _window: {
            "t-on-hashchange": this.onHashChange,
        },
        ".modal:not(.s_popup_no_backdrop)": {
            "t-on-click": this.onBackdropModalClick,
        },
    };

    setup() {
        log.lifecycle("Popup setup", () => ({ id: this.el.id }));
        this.cookieValue = true;
        this.modalEl = this.el.querySelector(".modal");
        /** @type {import("bootstrap").Modal} */
        this.bsModal = Modal.getOrCreateInstance(this.modalEl);
        this.registerCleanup(() => {
            for (const el of [this.bsModal._dialog, this.bsModal._element]) {
                el?.dispatchEvent(new Event("transitionend"));
            }
            this.bsModal.dispose();
        });

        this.modalShownOnClickEl = this.el.querySelector(
            ".modal[data-display='onClick']",
        );
        if (this.modalShownOnClickEl) {
            this.showModalBtnEl = document.querySelector(
                `[href="#${this.modalShownOnClickEl.id}"]`,
            );
            log.logic("Popup setup: onClick display", () => ({
                modalId: this.modalShownOnClickEl.id,
                hasShowBtn: !!this.showModalBtnEl,
            }));
            this.showPopupOnClick();
            return;
        }

        this.popupAlreadyShown = !!cookie.get(this.el.id);
        log.logic("Popup setup: cookie", () => ({
            id: this.el.id,
            popupAlreadyShown: this.popupAlreadyShown,
        }));
    }

    start() {
        const isMobile = uiUtils.getSize() < SIZES.LG;
        const emptyPopup = [
            ...this.el.querySelectorAll(".oe_structure > *:not(.s_popup_close)"),
        ].every((el) => {
            const visibilitySelectors = el.dataset.visibilitySelectors;
            const deviceInvisible = isMobile
                ? el.classList.contains("o_snippet_mobile_invisible")
                : el.classList.contains("o_snippet_desktop_invisible");
            return (
                (visibilitySelectors && el.matches(visibilitySelectors)) ||
                deviceInvisible
            );
        });
        log.pipeline("Popup start: bind decision", () => ({
            id: this.el.id,
            isMobile,
            emptyPopup,
            popupAlreadyShown: this.popupAlreadyShown,
            bind: !this.popupAlreadyShown && !emptyPopup,
        }));
        if (!this.popupAlreadyShown && !emptyPopup) {
            this.bindPopup();
        }
    }

    bindPopup() {
        let display = this.modalEl.dataset.display;
        let delay = parseInt(this.modalEl.dataset.showAfter);

        if (uiUtils.isSmall()) {
            if (display === "mouseExit") {
                display = "afterDelay";
                delay = 5000;
            }
        }

        log.pipeline("Popup bindPopup: trigger", () => ({
            id: this.el.id,
            configuredDisplay: this.modalEl.dataset.display,
            display,
            delay,
        }));
        if (display === "afterDelay") {
            this.waitForTimeout(this.showPopup, delay);
        } else if (display === "mouseExit") {
            this.addListener(document.body, "mouseleave", this.showPopup);
        }
    }

    canShowPopup() {
        return true;
    }

    hidePopup() {
        log.lifecycle("Popup hide", () => ({ id: this.el.id }));
        this.bsModal.hide();
    }

    showPopup() {
        if (this.popupAlreadyShown || !this.canShowPopup()) {
            log.logic("Popup showPopup: skipped", () => ({
                id: this.el.id,
                popupAlreadyShown: this.popupAlreadyShown,
            }));
            return;
        }
        log.lifecycle("Popup show", () => ({ id: this.el.id }));
        this.bsModal.show();
        this.registerCleanup(() => {
            this.modalEl.classList.remove("show");
            this.bsModal._hideModal();
        });
    }

    /**
     * @param {String} [hash]
     */
    showPopupOnClick(hash = browser.location.hash) {
        if (hash && hash.substring(1) === this.modalShownOnClickEl.id) {
            const urlWithoutHash = browser.location.href.replace(hash, "");
            browser.history.replaceState(null, null, urlWithoutHash);
            log.logic("Popup showPopupOnClick: hash matched", () => ({ hash }));
            this.showPopup();
        }
    }

    /**
     * @param {HTMLElement} primaryBtnEl
     */
    canBtnPrimaryClosePopup(primaryBtnEl) {
        return !(
            primaryBtnEl.classList.contains("s_website_form_send") ||
            primaryBtnEl.classList.contains("o_website_form_send")
        );
    }

    /**
     * @returns {Function}
     */
    trapFocus() {
        let tabableEls = getTabableElements(this.el);
        let previouslyFocusedEl;
        if (this.showModalBtnEl) {
            previouslyFocusedEl = this.showModalBtnEl;
        } else {
            previouslyFocusedEl = document.activeElement || document.body;
        }
        if (tabableEls.length) {
            tabableEls[0].focus();
            this.el.querySelector(".modal").scrollTop = 0;
        } else {
            this.el.focus();
        }
        if (this.el.querySelector(".s_popup_no_backdrop")) {
            log.logic("Popup trapFocus: no backdrop, focus restore only", () => ({
                id: this.el.id,
                tabable: tabableEls.length,
            }));
            this.addListener(
                this.el,
                "hide.bs.modal",
                () => previouslyFocusedEl.focus(),
                {
                    once: true,
                },
            );
            return;
        }
        const onKeydown = (ev) => {
            if (ev.key !== "Tab") {
                return;
            }
            tabableEls = getTabableElements(this.el);
            if (!tabableEls.length) {
                ev.preventDefault();
                return;
            }
            if (!ev.shiftKey && ev.target === tabableEls[tabableEls.length - 1]) {
                ev.preventDefault();
                tabableEls[0].focus();
            }
            if (ev.shiftKey && ev.target === tabableEls[0]) {
                ev.preventDefault();
                tabableEls[tabableEls.length - 1].focus();
            }
        };
        const removeOnKeydown = this.addListener(this.el, "keydown", onKeydown);
        this.addListener(
            this.el,
            "hide.bs.modal",
            () => {
                removeOnKeydown();
                previouslyFocusedEl.focus();
            },
            { once: true },
        );
    }

    onCloseClick() {
        this.hidePopup();
    }

    /**
     * @param {MouseEvent} ev
     */
    onBtnPrimaryClick(ev) {
        if (this.canBtnPrimaryClosePopup(ev.target)) {
            this.hidePopup();
        }
    }

    onHideModal() {
        const nbDays = this.modalEl.dataset.consentsDuration;
        cookie.set(this.el.id, this.cookieValue, nbDays * 24 * 60 * 60, "required");
        this.popupAlreadyShown = !this.modalShownOnClickEl;
        log.logic("Popup onHideModal: cookie set", () => ({
            id: this.el.id,
            cookieValue: this.cookieValue,
            nbDays,
            popupAlreadyShown: this.popupAlreadyShown,
        }));
    }

    /**
     * @param {HashChangeEvent} ev
     */
    onHashChange(ev) {
        if (this.modalShownOnClickEl) {
            this.showPopupOnClick(new URL(ev.newURL).hash);
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    onBackdropModalClick(ev) {
        if (ev.target === ev.currentTarget) {
            this.hidePopup();
        }
    }
}

registry.category("public.interactions").add("website.popup", Popup);
