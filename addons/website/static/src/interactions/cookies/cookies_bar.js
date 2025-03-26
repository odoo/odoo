import { Popup } from "@website/interactions/popup/popup";
import { registry } from "@web/core/registry";

import { cookie } from "@web/core/browser/cookie";
import { _t } from "@web/core/l10n/translation";
import { isVisible } from "@web/core/utils/ui";
import { setUtmsHtmlDataset } from "@website/utils/misc";

// Extending the Popup class with cookiebar functionality.
// This allows for refusing optional cookies for now and can be
// extended to picking which cookies categories are accepted.
export class CookiesBar extends Popup {
    static selector = "#website_cookies_bar";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _cookiesbus: () => this.services.website_cookies.bus,
    };
    dynamicContent = {
        ...this.dynamicContent,
        _cookiesbus: {
            "t-on-cookiesBar.show": this.onShowCookiesBar,
            "t-on-cookiesBar.toggle": this.onToggleCookiesBar,
        },
        "#cookies-consent-essential, #cookies-consent-all": { "t-on-click": this.onAcceptClick },
        // Override to avoid side effects on hide.
        ".js_close_popup": { "t-on-click": () => {} },
    };

    setup() {
        super.setup();
    }

    showPopup() {
        super.showPopup();

        const policyLinkEl = this.el.querySelector(".o_cookies_bar_text_policy");
        if (policyLinkEl && window.location.pathname === new URL(policyLinkEl.href).pathname) {
            this.onToggleCookiesBar();
        }
    }

    onToggleCookiesBar() {
        this.cookieValue = cookie.get(this.el.id);
        this.bsModal.toggle();
        // As we're using Bootstrap's events, the Popup class prevents the modal
        // from being shown after hiding it: override that behavior.
        this.popupAlreadyShown = false;
    }

    /**
     * @param {MouseEvent} ev
     */
    onAcceptClick(ev) {
        const isFullConsent = ev.currentTarget.id === "cookies-consent-all";
        this.cookieValue = `{"required": true, "optional": ${isFullConsent}, "ts": ${Date.now()}}`;
        if (isFullConsent) {
            document.dispatchEvent(new Event("optionalCookiesAccepted"));
        } else {
            document.dispatchEvent(new Event("optionalCookiesDenied"));
        }
        this.bsModal.hide();
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
        if ((currCookie && JSON.parse(currCookie).optional) || !this.popupAlreadyShown) {
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
