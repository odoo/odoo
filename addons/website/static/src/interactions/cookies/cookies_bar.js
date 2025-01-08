import { cookie } from "@web/core/browser/cookie";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { isVisible } from "@web/core/utils/ui";
import { setUtmsHtmlDataset } from "@website/utils/misc";
import { Popup } from "@website/interactions/popup/popup";
import { cloneContentEls } from "@website/js/utils";

// Extending the Popup class with cookiebar functionality.
// This allows for refusing optional cookies for now and can be
// extended to picking which cookies categories are accepted.
export class CookiesBar extends Popup {
    static selector = "#website_cookies_bar";
    dynamicContent = Object.assign(this.dynamicContent, {
        "#cookies-consent-essential, #cookies-consent-all": {
            "t-on-click": this.onAcceptClick,
        },
        // Override to avoid side effects on hide.
        ".js_close_popup": {
            "t-on-click": () => {},
        },
    });

    setup() {
        super.setup();
        this.showToggle();
    }

    start() {
        super.start();
        this.addListener(
            this.services.website_cookies.bus,
            "cookiesBar.show",
            this.onShowCookiesBar
        );
        this.addListener(
            this.services.website_cookies.bus,
            "cookiesBar.toggle",
            this.toggleCookiesBar,
        );
    }

    showPopup() {
        super.showPopup();
        if (this.toggleEl) {
            this.toggleCookiesBar();
        }
    }

    showToggle() {
        const policyLinkEl = this.el.querySelector(".o_cookies_bar_text_policy");
        if (policyLinkEl && window.location.pathname === new URL(policyLinkEl.href).pathname) {
            this.toggleEl = cloneContentEls(`
            <button class="o_cookies_bar_toggle btn btn-info btn-sm rounded-circle d-flex gap-2 align-items-center position-fixed pe-auto">
                <i class="fa fa-eye" alt="" aria-hidden="true"></i> <span class="o_cookies_bar_toggle_label"></span>
            </button>
            `).firstElementChild;
            this.insert(this.toggleEl, this.el, "beforebegin");
            this.services["public.interactions"].startInteractions(this.toggleEl);
        }
    }

    toggleCookiesBar() {
        this.bsModal.toggle();
        // As we're using Bootstrap's events, the Popup class prevents the modal
        // from being shown after hiding it: override that behavior.
        this._popupAlreadyShown = false;
        cookie.delete(this.el.id);
    }

    /**
     * @param {Event} ev
     */
    onAcceptClick(ev) {
        const isFullConsent = ev.target.id === "cookies-consent-all";
        this.cookieValue = `{"required": true, "optional": ${isFullConsent}}`;
        if (isFullConsent) {
            document.dispatchEvent(new Event("optionalCookiesAccepted"));
        }
        this.bsModal.hide();
        this.services.website_cookies.bus.trigger("cookiesBar.discard");
    }

    onHideModal() {
        super.onHideModal();
        const params = new URLSearchParams(window.location.search);
        const trackingFields = {
            utm_campaign: "odoo_utm_campaign",
            utm_source: "odoo_utm_source",
            utm_medium: "odoo_utm_medium",
        };
        for (const [key, value] of params) {
            if (key in trackingFields) {
                // Using same cookie expiration value as in python side
                cookie.set(trackingFields[key], value, 31 * 24 * 60 * 60, "optional");
            }
        }
        setUtmsHtmlDataset();
    }

    /**
     * Reopens the cookies bar if it was closed.
     */
    onShowCookiesBar() {
        const currCookie = cookie.get(this.el.id);
        if (currCookie && JSON.parse(currCookie).optional || !this._popupAlreadyShown) {
            return;
        }
        this.bsModal.show();

        // The cookies bar remains hidden, most probably because of the browser
        // or an extension: notify the user because "nothing happens when I
        // click" is never good.
        if (!isVisible(this.modalEl)) {
            window.alert(_t("Our cookies bar was blocked by your browser or an extension."));
            return;
        }
        this.modalEl.focus();
    }
}

registry.category("public.interactions").add("website.cookies_bar", CookiesBar);
