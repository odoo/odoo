import { cookie } from "@web/core/browser/cookie";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { utils as uiUtils, SIZES } from "@web/core/ui/ui_service";
import { Interaction } from "@website/core/interaction";

export class Popup extends Interaction {
    static selector = ".s_popup:not(#website_cookies_bar)";
    dynamicContent = {
        ".js_close_popup": {
            "t-on-click": this.onCloseClick,
        },
        ".btn-primary": {
            "t-on-click": this.onBtnPrimaryClick,
        },
        "_root": {
            "t-on-hide.bs.modal": this.onHideModal,
            "t-on-show.bs.modal": this.onShowModal,
        },
        "_window": {
            "t-on-hashchange": this.onHashChange,
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
            // Check if a hash exists and if the modal needs to be opened when
            // the page loads (e.g. The user has clicked a button on the
            // "Contact us" page to open a popup on the homepage).
            this.showPopupOnClick();
            return;
        }

        this._popupAlreadyShown = !!cookie.get(this.el.id);
    }

    start() {
        // Check if every child element of the popup is conditionally hidden,
        // and if so, never show an empty popup.
        // config.device.isMobile is true if the device is <= SM, but the device
        // visibility option uses < LG to hide on mobile. So compute it here.
        const isMobile = uiUtils.getSize() < SIZES.LG;
        const emptyPopup = [
            ...this.el.querySelectorAll(".oe_structure > *:not(.s_popup_close)")
        ].every((el) => {
            const visibilitySelectors = el.dataset.visibilitySelectors;
            const deviceInvisible = isMobile
                ? el.classList.contains("o_snippet_mobile_invisible")
                : el.classList.contains("o_snippet_desktop_invisible");
            return (visibilitySelectors && el.matches(visibilitySelectors)) || deviceInvisible;
        });
        if (!this._popupAlreadyShown && !emptyPopup) {
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
        if (this._popupAlreadyShown || !this.canShowPopup()) {
            return;
        }
        this.bsModal.show();
    }

    /**
     * @param {String} [hash]
     */
    showPopupOnClick(hash = window.location.hash) {
        // If a hash exists in the URL and it corresponds to the ID of the modal,
        // then we open the modal.
        if (hash && hash.substring(1) === this.modalShownOnClickEl.id) {
            // We remove the hash from the URL because otherwise the popup
            // cannot open again after being closed.
            const urlWithoutHash = window.location.href.replace(hash, "");
            window.history.replaceState(null, null, urlWithoutHash);
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
            primaryBtnEl.classList.contains("s_website_form_send")
            || primaryBtnEl.classList.contains("o_website_form_send")
        );
    }

    onCloseClick() {
        this.hidePopup();
    }

    /**
     * @param {Event} ev
     */
    onBtnPrimaryClick(ev) {
        if (this.canBtnPrimaryClosePopup(ev.target)) {
            this.hidePopup();
        }
    }

    onHideModal() {
        const nbDays = this.modalEl.dataset.consentsDuration;
        cookie.set(this.el.id, this.cookieValue, nbDays * 24 * 60 * 60, "required");
        this._popupAlreadyShown = !this.modalShownOnClickEl;

        this.el.querySelectorAll(".media_iframe_video iframe").forEach((iframeEl) => {
            iframeEl.src = "";
        });
    }

    onShowModal() {
        this.el.querySelectorAll(".media_iframe_video").forEach((mediaEl) => {
            // TODO still oeExpression to remove someday
            this.services.website_cookies.manageIframeSrc(
                mediaEl.querySelector("iframe"),
                mediaEl.dataset.oeExpression || mediaEl.dataset.src
            );
        });
    }

    /**
     * @param {Event} ev
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
}

registry.category("website.active_elements").add("website.popup", Popup);
