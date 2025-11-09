import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { utils as uiUtils, SIZES } from "@web/core/ui/ui_service";
import { getTabableElements } from "@web/core/utils/ui";

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
            // Here, bootstrap's data-bs-backdrop attribute is not used and
            // we use a custom click handler instead to dismiss the popup on
            // click outside as we do not use bootstrap native backdrop.
            // See MODAL_BACKDROP_WEBSITE.
            "t-on-click": this.onBackdropModalClick,
        },
    };

    setup() {
        this.cookieValue = true;
        this.modalEl = this.el.querySelector(".modal");
        /** @type {import("bootstrap").Modal} */
        this.bsModal = window.Modal.getOrCreateInstance(this.modalEl);
        this.registerCleanup(() => {
            this.bsModal.dispose();
        });

        this.modalShownOnClickEl = this.el.querySelector(".modal[data-display='onClick']");
        if (this.modalShownOnClickEl) {
            this.showModalBtnEl = document.querySelector(
                `[href="#${this.modalShownOnClickEl.id}"]`
            );
            // Check if a hash exists and if the modal needs to be opened when
            // the page loads (e.g. The user has clicked a button on the
            // "Contact us" page to open a popup on the homepage).
            this.showPopupOnClick();
            return;
        }

        this.popupAlreadyShown = !!cookie.get(this.el.id);
    }

    start() {
        // Check if every child element of the popup is conditionally hidden,
        // and if so, never show an empty popup.
        // config.device.isMobile is true if the device is <= SM, but the device
        // visibility option uses < LG to hide on mobile. So compute it here.
        const isMobile = uiUtils.getSize() < SIZES.LG;
        const emptyPopup = [
            ...this.el.querySelectorAll(".oe_structure > *:not(.s_popup_close)"),
        ].every((el) => {
            const visibilitySelectors = el.dataset.visibilitySelectors;
            const deviceInvisible = isMobile
                ? el.classList.contains("o_snippet_mobile_invisible")
                : el.classList.contains("o_snippet_desktop_invisible");
            return (visibilitySelectors && el.matches(visibilitySelectors)) || deviceInvisible;
        });
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
        this.bsModal.hide();
    }

    showPopup() {
        if (this.popupAlreadyShown || !this.canShowPopup()) {
            return;
        }
        this.bsModal.show();
        this.registerCleanup(() => {
            // Do not call .hide() directly, because it is queued whereas
            // .dispose() is not, making it crash. As we don't have to wait for
            // animations here, bypass the issue with ._hideModal().
            // Additionally, .hide() triggers `hide.bs.modal`, which triggers
            // onHideModal() and sets a cookie: we don't want that on destroy.
            this.modalEl.classList.remove("show");
            this.bsModal._hideModal();
        });
    }

    /**
     * @param {String} [hash]
     */
    showPopupOnClick(hash = browser.location.hash) {
        // If a hash exists in the URL and it corresponds to the ID of the modal,
        // then we open the modal.
        if (hash && hash.substring(1) === this.modalShownOnClickEl.id) {
            // We remove the hash from the URL because otherwise the popup
            // cannot open again after being closed.
            const urlWithoutHash = browser.location.href.replace(hash, "");
            browser.history.replaceState(null, null, urlWithoutHash);
            this.showPopup();
        }
    }

    /**
     * Checks if the given primary button should allow or not to close the
     * modal.
     *
     * @param {HTMLElement} primaryBtnEl
     */
    canBtnPrimaryClosePopup(primaryBtnEl) {
        return !(
            primaryBtnEl.classList.contains("s_website_form_send") ||
            primaryBtnEl.classList.contains("o_website_form_send")
        );
    }

    /**
     * Traps the focus within the modal.
     *
     * @returns {Function} refocuses the element that was focused before the
     * modal opened.
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
        // The focus should stay free for no backdrop popups.
        if (this.el.querySelector(".s_popup_no_backdrop")) {
            this.addListener(this.el, "hide.bs.modal", () => previouslyFocusedEl.focus(), {
                once: true,
            });
            return;
        }
        const onKeydown = (ev) => {
            if (ev.key !== "Tab") {
                return;
            }
            // Update tabableEls: they might have changed in the meantime.
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
            { once: true }
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
    }

    /**
     * @param {HashChangeEvent} ev
     */
    onHashChange(ev) {
        if (this.modalShownOnClickEl) {
            // Keep the new hash from the event to avoid conflict with the eCommerce
            // hash attributes managing.
            // TODO : it should not have been a hash at all for ecommerce, but a
            // query string parameter
            this.showPopupOnClick(new URL(ev.newURL).hash);
        }
    }

    /**
     * Handles clicks outside the popup to dismiss it.
     *
     * @param {MouseEvent} ev
     */
    onBackdropModalClick(ev) {
        if (ev.target === ev.currentTarget) {
            this.hidePopup();
        }
    }
}

registry.category("public.interactions").add("website.popup", Popup);
