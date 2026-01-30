import { Popup } from "@website/interactions/popup/popup";
import { registry } from "@web/core/registry";

import { cookie } from "@web/core/browser/cookie";
import { _t } from "@web/core/l10n/translation";
import { isVisible } from "@web/core/utils/ui";
import { cloneContentEls } from "@website/js/utils";
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
        ".btn-primary": { "t-on-click": () => {} },
        ".modal": {
            "t-on-keydown.capture": (ev) => {
                if (ev.key === "Escape") {
                    // Circumvent Bootstrap's keydown behavior which triggers a
                    // UI glitch.
                    ev.stopImmediatePropagation();
                }
            },
        },
    };

    setup() {
        super.setup();
        this.showToggle();
    }

    start() {
        super.start();

        // Add a link to the cookie policy page in the copyright footer.
        // TODO: In master, add this link via XML.
        const copyrightFooterContainerEl = document.querySelector(
            ".o_footer_copyright_name"
        )?.parentElement;
        if (copyrightFooterContainerEl) {
            const cookiePolicyLinkEl = cloneContentEls(`
                <p><a href="/cookie-policy" class="o_cookie_policy_link">${_t(
                    "Cookie Policy"
                )}</a></p>
            `).firstElementChild;
            this.insert(cookiePolicyLinkEl, copyrightFooterContainerEl);
        }

        // Since cookie preferences can be changed, update the gtag script that
        // toggles the gtag consent. So, when the user modifies their cookie
        // preference their gtag consent is also updated.
        // TODO: In master, update the #tracking_code_config script via XML.
        const originalTrackingCodeScriptEl = document.querySelector("#tracking_code_config");
        if (originalTrackingCodeScriptEl) {
            // Remove the one-time event listener added by the original script
            document.removeEventListener("optionalCookiesAccepted", window.allConsentsGranted);

            // Create a new script element
            const updatedTrackingCodeScript = `
                window.dataLayer = window.dataLayer || [];
                function gtag() {
                    dataLayer.push(arguments);
                }

                function updateConsents(consentState) {
                    gtag("consent", "update", {
                        "ad_storage": consentState,
                        "ad_user_data": consentState,
                        "ad_personalization": consentState,
                        "analytics_storage": consentState,
                    });
                }

                document.addEventListener("optionalCookiesAccepted", () => {
                    updateConsents("granted");
                });

                document.addEventListener("optionalCookiesDenied", () => {
                    updateConsents("denied");
                });
            `;
            const newScriptEl = document.createElement("script");
            newScriptEl.id = "tracking_code_config";
            newScriptEl.textContent = updatedTrackingCodeScript;

            // Replace the original script with the new one
            originalTrackingCodeScriptEl.parentNode.replaceChild(
                newScriptEl,
                originalTrackingCodeScriptEl
            );
        }
    }

    showPopup() {
        super.showPopup();
        if (this.toggleEl) {
            this.onToggleCookiesBar();
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
